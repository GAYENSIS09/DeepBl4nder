"""Routeur multi-fournisseurs (vote / fallback) + cooldown, compatible UnifiedLLM.

``LLMRouter`` répond à l'interface de ``UnifiedLLM`` (``call`` / ``acall``)
donc s'injecte directement dans les agents NOOA. Santé par fournisseur,
cooldown après échec, observabilité (``provider_stats`` / ``routing_stats``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from nooa.unifiedllm import RetryConfig, UnifiedLLM
from nooa.unifiedllm.registry import get_llm_client

from .discovery import discover_models
from .errors import _acall_with_budget_retry, _apply_global_max_tokens, _classify_error
from .providers import LLMProvider, PROVIDERS, configured_providers, get_provider
from .selection import compose_litellm_ids, select_models, selection_rule_for

logger = logging.getLogger("DeepBl4nder.llm.router")
@dataclass
class ProviderHealth:
    """Santé d'un fournisseur : compteurs, victoires, cooldown, erreur."""

    successes: int = 0
    wins: int = 0
    failures: int = 0
    cooldown_until: float = 0.0
    last_error: str | None = None

    def is_cooling(self, now: float) -> bool:
        return self.cooldown_until > now


def _signature(result: Any) -> str:
    """Empreinte canonique d'une réponse : deux réponses identiques votent pareil."""
    try:
        return json.dumps(result, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return str(result)


def model_name_of(llm: Any) -> str:
    """Nom du modèle d'un client LLM, quel que soit son exposé.

    ``UnifiedLLM`` et ``LLMRouter`` exposent ``model`` comme attribut string ;
    d'anciens clients (ou des doublures de test) peuvent l'exposer en méthode.
    """
    name = getattr(llm, "model", None)
    if callable(name):
        try:
            name = name()
        except Exception:  # noqa: BLE001
            return "unknown"
    return str(name) if name else "unknown"


class LLMRouter:
    """Routeur multi-fournisseurs : vote de tous + cooldown simple.

    Compatible drop-in avec ``UnifiedLLM`` (``call`` / ``acall``) donc
    directement injectable dans les agents NOOA.
    """

    def __init__(
        self,
        provider_ids: list[str] | None = None,
        cooldown: float = 30.0,
        client_factory: Callable[..., UnifiedLLM] | None = None,
        clock: Callable[[], float] | None = None,
        mode: str | None = None,
        discover: bool | None = None,
    ) -> None:
        self._cooldown = cooldown if cooldown is not None else 30.0
        self._client_factory = client_factory or get_llm_client
        self._clock = clock or time.time
        self._configured_ids: list[str] = [
            pid.strip() for pid in (provider_ids or []) if pid.strip()
        ]
        # Mode d'appel :
        # - "vote" : tous les fournisseurs répondent, majorité + tie-break santé
        #   (qualité maximale, consomme les quotas de tous à chaque appel) ;
        # - "fallback" : premier fournisseur sain dans l'ordre du pool ; on ne
        #   passe au suivant qu'en cas d'échec (économique, adapté à la prod).
        resolved = (
            mode or os.environ.get("DeepBl4nder_LLM_MODE", "vote")
        ).strip().lower()
        self._mode = resolved if resolved in ("vote", "fallback") else "vote"

        self._providers = self._discover()
        # Modèles actifs par fournisseur : découverts via GET /models puis
        # filtrés par les règles (MODEL_SELECTION_RULES). Vide = repli statique.
        self._active_models: dict[str, tuple[str, ...]] = {}
        discover_env = os.environ.get(
            "DeepBl4nder_DISCOVER_MODELS", "1"
        ).strip().lower() not in {"0", "false", "off"}
        # Priorité : paramètre explicite ``discover`` > env > heuristique
        # (fabrique injectée = tests/outillage → pas de réseau).
        if discover is not None:
            self._discover_enabled = discover
        else:
            self._discover_enabled = discover_env and client_factory is None
            if client_factory is not None:
                logger.debug("Découverte des modèles ignorée (fabrique client injectée).")
        if self._discover_enabled:
            self._refresh_active_models()
        else:
            logger.info("Découverte dynamique des modèles désactivée → listes statiques.")
        self._health: dict[str, ProviderHealth] = {}
        self._clients: dict[str, UnifiedLLM] = {}
        # Dernière décision réelle du vote : (provider_id, modèle) — None avant
        # tout appel. Sert à rapporter le fournisseur réellement utilisé
        # (événements LLM, observabilité) plutôt que la config statique.
        self._last_decision: tuple[str, str] | None = None
        self._last_attempt: tuple[str, str, str] | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ pool

    def _discover(self) -> list[LLMProvider]:
        """Construit le pool.

        - ids explicites (constructeur) : pool strict, dans cet ordre ;
        - sinon : pool restreint (env ``DeepBl4nder_LLM_PROVIDERS``, fichier
          ``~/.deepbl4nder/llm.json`` → clé ``provider_ids``) ; si le pool
          restreint est vide : tous les fournisseurs de ``PROVIDERS`` dont la
          clé d'API est définie.
        """
        if self._configured_ids:
            providers = [get_provider(pid) for pid in self._configured_ids]
        else:
            configured = configured_providers()
            if configured:
                providers = [get_provider(pid) for pid in configured]
            else:
                providers = list(PROVIDERS.values())

        pool = [p for p in providers if p.is_available()]
        if not pool:
            raise RuntimeError(self._missing_keys_message())
        return pool

    def _missing_keys_message(self) -> str:
        msg = "Aucun fournisseur LLM configuré."
        if self._configured_ids:
            keys = ", ".join(
                sorted(
                    {
                        PROVIDERS[pid].api_key_env
                        for pid in self._configured_ids
                        if pid in PROVIDERS
                    }
                )
            )
            msg += f" Vérifiez les clés suivantes dans .env : {keys}."
        else:
            msg += (
                " Définissez au moins une clé d'API (GEMINI_API_KEY, GROQ_API_KEY, "
                "NVIDIA_API_KEY, OPENROUTER_API_KEY, CLOUDFLARE_API_KEY)."
            )
        return msg

    def models_for(self, provider: LLMProvider) -> list[str]:
        """Candidats actifs du fournisseur : découverts, sinon repli statique."""
        active = self._active_models.get(provider.id)
        if active:
            return list(active)
        return [provider.model()]

    def _refresh_active_models(self) -> None:
        """Interroge chaque fournisseur et applique les règles de sélection."""
        for provider in self._providers:
            raw = discover_models(provider)
            if not raw:
                continue
            rule = selection_rule_for(provider.id)
            chosen_native = select_models(list(raw), rule)
            if not chosen_native:
                logger.warning(
                    "Règles de sélection : aucun modèle retenu pour %s (%d candidats bruts) → liste statique.",
                    provider.id,
                    len(raw),
                )
                continue
            chosen = compose_litellm_ids(provider, chosen_native, rule)
            self._active_models[provider.id] = chosen
            static = provider.model()
            note = (
                "" if static == chosen[0]
                else f" (le statique {static!r} est remplacé)"
            )
            logger.info(
                "Modèles actifs %s : %s — via découverte /models%s",
                provider.id,
                list(chosen),
                note,
            )

    def _model_for(self, provider: LLMProvider) -> str:
        """Modèle à utiliser : premier découvert, sinon repli statique."""
        active = self._active_models.get(provider.id)
        return active[0] if active else provider.model()

    def models_source(self, provider: LLMProvider) -> str:
        """Provenance de la liste : 'découverte' ou 'statique'."""
        return "découverte" if self._active_models.get(provider.id) else "statique"

    @property
    def model(self) -> str:
        """Modèle du premier fournisseur du pool (affichage / métadonnées).

        Attribut (et non méthode) pour être drop-in compatible avec
        ``UnifiedLLM`` : NOOA lit ``llm_client.model`` et l'injecte tel quel
        dans ``LLMComplete(model_name=...)`` qui exige un ``str``.

        Attention : valeur statique (config du pool), pas le modèle réellement
        gagnant du dernier vote — voir ``last_model`` / ``last_provider_id``.
        """
        if not self._providers:
            return "unknown"
        return self._model_for(self._providers[0])

    @property
    def last_provider_id(self) -> str | None:
        """Identifiant du fournisseur gagnant du dernier vote (None avant tout appel)."""
        with self._lock:
            decision = self._last_decision
        return decision[0] if decision else None

    @property
    def last_model(self) -> str | None:
        """Modèle du fournisseur gagnant du dernier vote (None avant tout appel)."""
        with self._lock:
            decision = self._last_decision
        return decision[1] if decision else None

    def _set_last_decision(self, provider_id: str) -> None:
        """Mémorise la décision réelle du dernier vote (provider + modèle actif)."""
        model = next(
            (self._model_for(p) for p in self._providers if p.id == provider_id), None
        )
        with self._lock:
            self._last_decision = (provider_id, model) if model else None

    @property
    def last_attempt(self) -> tuple[str, str, str] | None:
        """(fournisseur, modèle, classe d'erreur) de la dernière tentative.

        Renseigné À CHAQUE échec d'un modèle — même quand aucun fournisseur
        ne réussit : l'UI voit la recherche/rotation en cours au lieu d'un
        "no reply" figé. ``None`` avant toute tentative.
        """
        with self._lock:
            return self._last_attempt

    def _set_last_attempt(self, provider_id: str, model: str, kind: str) -> None:
        """Mémorise la dernière tentative (appel échoué) d'un fournisseur."""
        with self._lock:
            self._last_attempt = (provider_id, model, kind)

    def providers(self) -> list[LLMProvider]:
        return list(self._providers)

    # -------------------------------------------------------------- routing

    def _health_for(self, provider_id: str) -> ProviderHealth:
        """Santé d'un fournisseur — créée à la volée."""
        with self._lock:
            health = self._health.get(provider_id)
            if health is None:
                health = ProviderHealth()
                self._health[provider_id] = health
        return health

    def _provider_is_cooling(self, provider: LLMProvider, now: float) -> bool:
        return self._health_for(provider.id).is_cooling(now)

    def _get_client(self, provider: LLMProvider, model: str | None = None) -> UnifiedLLM:
        resolved_model = model or self._model_for(provider)
        cache_key = f"{provider.id}::{resolved_model}"
        with self._lock:
            client = self._clients.get(cache_key)
        if client is not None:
            return client
        kwargs: dict[str, Any] = {
            # Prompt caching activé : garde le préfixe stable (system prompt,
            # skills, schéma) dans le cache du fournisseur entre appels →
            # réduit la latence et le coût sur les runs longs (agents à tours
            # multiples). Désactivable via env si un fournisseur se comporte
            # mal :
            #   DeepBl4nder_LLM_CACHE=off
            "cache_control_injection_points": (
                [] if os.environ.get("DeepBl4nder_LLM_CACHE", "1").strip().lower()
                in {"0", "false", "off"}
                else ["messages"]
            ),
            # Fail fast : le vote s'appuie sur les autres fournisseurs en cas
            # d'échec. Un seul retry court pour les erreurs transitoires,
            # aucun backoff long sur rate limit (sinon un 429 bloque le run
            # et chaque tentative consomme des tokens inutilement).
            "retry_config": RetryConfig(
                max_retries=1,
                base_delay=1.0,
                rate_limit_extra_retries=0,
                rate_limit_base_delay=1.0,
            ),
        }
        if api_key := provider.api_key():
            kwargs["api_key"] = api_key
        if api_base := provider.api_base():
            kwargs["api_base"] = api_base
        client = self._client_factory(resolved_model, **kwargs)
        with self._lock:
            self._clients[cache_key] = client
        return client

    async def _call_provider(
        self,
        provider: LLMProvider,
        messages: list[dict[str, Any]],
        tools: list[Any] | None,
        output_model: type[Any] | None,
        kwargs: dict[str, Any],
    ) -> tuple[Any, str]:
        """Essaie les modèles candidats du fournisseur dans l'ordre.

        Rotation intra-fournisseur : une erreur liée AU MODÈLE (404,
        déprécié) ou transitoire (503 surcharge) tente le candidat suivant —
        ex. 3.7-flash saturé → 3.6-flash → 3.5-flash. Une erreur de COMPTE ou
        de REQUÊTE (auth, quota/TPM, contexte trop long) est sans espoir pour
        les autres candidats : relevée immédiatement vers le fournisseur
        suivant. Retourne ``(résultat, modèle utilisé)``.
        """
        last_exc: Exception | None = None
        for model in self.models_for(provider):
            client = self._get_client(provider, model)
            try:
                result, _downgraded = await _acall_with_budget_retry(
                    client, messages, tools, output_model, kwargs
                )
                return result, model
            except Exception as exc:  # noqa: BLE001
                kind = _classify_error(exc)
                last_exc = exc
                self._set_last_attempt(provider.id, model, kind)
                if kind in {"auth", "rate_limit", "context"}:
                    raise
                logger.info(
                    "Modèle %s indisponible (%s) → candidat suivant chez %s",
                    model,
                    kind,
                    provider.id,
                )
        assert last_exc is not None  # models_for() ne retourne jamais []
        raise last_exc

    def _record_success(self, provider: LLMProvider) -> None:
        health = self._health_for(provider.id)
        with self._lock:
            health.successes += 1
            health.cooldown_until = 0.0
            health.last_error = None

    def _record_failure(self, provider: LLMProvider, error: Exception) -> str:
        kind = _classify_error(error)
        now = self._clock()
        health = self._health_for(provider.id)
        with self._lock:
            health.failures += 1
            health.last_error = str(error)[:500]
            health.cooldown_until = now + self._cooldown
        logger.error(
            "LLM %s en échec (%s) → exclu du vote pendant %gs : %s",
            provider.id,
            kind,
            self._cooldown,
            str(error)[:300],
        )
        return str(error)

    def _record_win(self, provider_id: str) -> None:
        health = self._health_for(provider_id)
        with self._lock:
            health.wins += 1

    def _decide(self, results: dict[str, Any]) -> Any:
        """Choisit la réponse : majorité, puis santé (victoires, succès).

        Les réponses identiques forment un bloc ; le bloc le plus nombreux
        gagne. En cas d'égalité, le fournisseur le plus fiable du bloc l'emporte
        (ordre de priorité : victoires de vote, puis succès, puis ordre du pool).
        """
        sizes: dict[str, int] = {}
        for pid, result in results.items():
            sizes[pid] = sum(1 for other in results.values() if _signature(other) == _signature(result))

        def _score(pid: str) -> tuple[int, int, int, int]:
            health = self._health_for(pid)
            return (sizes[pid], health.wins, health.successes, -health.failures)

        winner = max(results, key=_score)
        self._record_win(winner)
        self._set_last_decision(winner)
        logger.info(
            "Vote LLM : gagnant=%s (bloc %d/%d)",
            winner,
            sizes[winner],
            len(results),
        )
        return results[winner]

    # ------------------------------------------------------------- appel LLM

    async def acall(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Appel asynchrone : fallback séquentiel ou vote selon le mode."""
        if not messages:
            logger.warning("LLM : messages vide/indéfini → payload de secours")
            messages = [{"role": "user", "content": ""}]
        now = self._clock()
        voters = [p for p in self._providers if not self._provider_is_cooling(p, now)]
        logger.debug(
            "Appel LLM mode=%s pool=%s sains=%s max_tokens=%s",
            self._mode,
            [p.id for p in self._providers],
            [p.id for p in voters],
            kwargs.get("max_tokens"),
        )
        if not voters:
            # Tout est en cooldown : on retente quand même (auto-réparation).
            voters = list(self._providers)
        if not voters:
            raise RuntimeError(self._missing_keys_message())

        kwargs = _apply_global_max_tokens(kwargs)

        if self._mode == "fallback":
            return await self._acall_fallback(messages, tools, output_model, voters, kwargs)
        return await self._acall_vote(messages, tools, output_model, voters, kwargs)

    async def _acall_fallback(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None,
        output_model: type[Any] | None,
        candidates: list[LLMProvider],
        kwargs: dict[str, Any],
    ) -> Any:
        """Mode production : essaie les fournisseurs dans l'ordre du pool.

        Un seul fournisseur sain est sollicité par appel (quotas préservés) ;
        en cas d'échec on descend la liste jusqu'à un succès ou épuisement.
        """
        errors: list[tuple[str, str]] = []
        for provider in candidates:
            started = time.perf_counter()
            logger.debug("Fallback : essai %s", provider.id)
            try:
                result, model_used = await self._call_provider(
                    provider, messages, tools, output_model, kwargs
                )
            except Exception as exc:  # noqa: BLE001
                elapsed = time.perf_counter() - started
                logger.warning(
                    "LLM %s a échoué après %.2fs (%s)",
                    provider.id,
                    elapsed,
                    str(exc)[:200],
                )
                errors.append((provider.id, self._record_failure(provider, exc)))
                continue
            elapsed = time.perf_counter() - started
            logger.info(
                "LLM %s a répondu en %.2fs (fallback, modèle %s)",
                provider.id,
                elapsed,
                model_used,
            )
            self._record_success(provider)
            self._record_win(provider.id)
            self._set_last_decision(provider.id)
            return result

        detail = "; ".join(f"{pid}: {msg[:160]}" for pid, msg in errors) or "inconnue"
        logger.error("Tous les fournisseurs LLM ont échoué — %s", detail)
        raise RuntimeError(
            f"Tous les fournisseurs LLM ont échoué. Erreurs par fournisseur : {detail}"
        )

    async def _acall_vote(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None,
        output_model: type[Any] | None,
        voters: list[LLMProvider],
        kwargs: dict[str, Any],
    ) -> Any:
        """Mode expérimental : tous les fournisseurs votent, la majorité gagne."""
        async def _vote(provider: LLMProvider) -> tuple[LLMProvider, Any, float]:
            started = time.perf_counter()
            try:
                result, _model_used = await self._call_provider(
                    provider, messages, tools, output_model, kwargs
                )
                return provider, result, time.perf_counter() - started
            except Exception as exc:  # noqa: BLE001
                return provider, exc, time.perf_counter() - started

        logger.info("Vote LLM démarré : fournisseurs=%s", [p.id for p in voters])
        outcomes = await asyncio.gather(*(_vote(p) for p in voters))

        results: dict[str, Any] = {}
        errors: list[tuple[str, str]] = []
        for provider, outcome, elapsed in outcomes:
            if isinstance(outcome, Exception):
                logger.warning(
                    "LLM %s a échoué après %.2fs (%s)",
                    provider.id,
                    elapsed,
                    str(outcome)[:200],
                )
                errors.append((provider.id, self._record_failure(provider, outcome)))
            else:
                results[provider.id] = outcome
                self._record_success(provider)
                logger.info("LLM %s a répondu en %.2fs", provider.id, elapsed)

        if not results:
            detail = "; ".join(f"{pid}: {msg[:160]}" for pid, msg in errors) or "inconnue"
            logger.error("Tous les fournisseurs LLM ont échoué — %s", detail)
            raise RuntimeError(
                f"Tous les fournisseurs LLM ont échoué. Erreurs par fournisseur : {detail}"
            )
        return self._decide(results)

    def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Appel synchrone : meme logique de vote que ``acall``.

        Si un event loop tourne deja (contexte async), on utilisera ``acall``
        a la place. Ce ``call`` est un fallback pour le code sync pur.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.acall(messages, tools=tools, output_model=output_model, **kwargs),
                )
                return future.result(timeout=120)

        return asyncio.run(self.acall(messages, tools=tools, output_model=output_model, **kwargs))

    def close(self) -> None:
        for client in self._clients.values():
            close = getattr(client, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:  # noqa: BLE001
                    pass
        self._clients.clear()

    # -------------------------------------------------------------- observ.

    def provider_stats(self, provider: LLMProvider) -> dict[str, Any]:
        """Statistiques d'un fournisseur, agrégées + ventilation par modèle."""
        now = self._clock()
        health = self._health_for(provider.id)
        model_stats = [
            {
                "model": model,
                "successes": health.successes,
                "failures": health.failures,
                "cooldown_remaining_s": max(0.0, health.cooldown_until - now),
                "last_error": health.last_error,
            }
            for model in self.models_for(provider)
        ]
        return {
            "id": provider.id,
            "model": self._model_for(provider),
            "base_url": provider.resolved_base_url(),
            "models_source": self.models_source(provider),
            "models": model_stats,
            "successes": health.successes,
            "failures": health.failures,
            "wins": health.wins,
            "cooldown_remaining_s": max(0.0, health.cooldown_until - now),
            "last_error": health.last_error,
        }

    def routing_stats(self) -> dict[str, Any]:
        """Résumé observable du routeur (santé par fournisseur, sans clés)."""
        return {
            "rotation": self._mode,
            "cooldown_seconds": self._cooldown,
            "pool": [p.id for p in self._providers],
            "providers": [self.provider_stats(p) for p in self._providers],
        }
