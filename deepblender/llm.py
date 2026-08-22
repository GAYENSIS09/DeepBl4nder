"""Gestion robuste des fournisseurs LLM : pool multi-fournisseurs + vote.

Le registre ``PROVIDERS`` décrit chaque fournisseur via la classe
``LLMProvider`` (id, clé d'API, base URL, modèles). Aucune configuration n'est
lue dans l'environnement en dehors des clés d'API : le pool, les modèles et les
URLs sont définis en dur dans ``PROVIDERS``.

Le ``LLMRouter`` consulte TOUS les fournisseurs du pool à chaque appel (même le
premier) et choisit la réponse par vote :

- tous les fournisseurs disponibles répondent en parallèle ;
- les réponses identiques forment une majorité → c'est la réponse retenue ;
- en cas d'égalité, la santé historique départage (fournisseur qui a gagné
  le plus de votes précédemment, puis le plus de succès) ;
- un fournisseur en échec (429, 5xx, timeout, 404 modèle…) passe en
  ``cooldown`` fixe et est réintégré automatiquement quand il refroidit ;
  s'il est en cooldown, il ne participe pas au vote suivant.

Sélection du pool (simple et explicite) :

- ``LLMRouter(provider_ids=[...])`` (ou ``get_router`` / ``build_llm``) : pool
  strict, dans cet ordre ;
- sinon : tous les fournisseurs de ``PROVIDERS`` dont la clé d'API est définie.

Seule variable d'environnement lue hors clés d'API : ``CLOUDFLARE_ACCOUNT_ID``,
requise pour résoudre l'URL Workers AI de Cloudflare (liée à sa clé d'API).
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from nooa.unifiedllm import RetryConfig, UnifiedLLM
from nooa.unifiedllm.registry import get_llm_client

# Fake client pour tests sans quota (disponible dans nooa 0.0.8+)
try:
    from nooa.unifiedllm.fake import FakeLLMClient
except ImportError:
    FakeLLMClient = None  # type: ignore[assignment,misc]


@dataclass(frozen=True)
class LLMProvider:
    """Fournisseur LLM : clé d'API, base URL et modèles, en dur dans ``PROVIDERS``."""

    id: str
    api_key_env: str
    base_url: str
    models: tuple[str, ...]

    def default_model(self) -> str:
        """Premier modèle disponible (seul modèle actif de ce fournisseur)."""
        return self.models[0]

    def model(self) -> str:
        """Modèle actif : fixé dans le registre (plus de surcharge .env)."""
        return self.default_model()

    def api_key(self) -> str | None:
        """Clé d'API dédiée (seule lecture d'environnement du module)."""
        return os.getenv(self.api_key_env)

    def is_available(self) -> bool:
        """Un fournisseur est utilisable s'il a sa clé dédiée."""
        return bool(self.api_key())

    def api_base(self) -> str | None:
        """Base URL : celle du registre pour un serveur local, sinon None
        (litellm connaît l'URL officielle du fournisseur)."""
        if self.id == "local":
            return self.base_url
        return None

    def resolved_base_url(self) -> str:
        """Base URL effective, placeholders substitués (ex. ``ACCOUNT_ID`` cloudflare).

        Cloudflare exige l'identifiant de compte dans l'URL ; litellm le lit
        aussi à l'appel via ``CLOUDFLARE_ACCOUNT_ID``, cette méthode sert à
        l'affichage (config / stats) sans placeholder brut.
        """
        custom = self.api_base()
        if custom:
            return custom
        if "ACCOUNT_ID" in self.base_url:
            return self.base_url.replace("ACCOUNT_ID", os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
        return self.base_url

    def config(self) -> dict[str, Any]:
        """Résumé de configuration (sans exposer la clé)."""
        return {
            "id": self.id,
            "base_url": self.resolved_base_url(),
            "model": self.model(),
            "api_key_configured": bool(self.api_key()),
        }


PROVIDERS: dict[str, LLMProvider] = {
    "gemini": LLMProvider(
        id="gemini",
        api_key_env="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        models=(
            "gemini/gemini-3.6-flash",
            "gemini/gemini-3.5-flash",
            "gemini/gemini-2.5-pro",
        ),
    ),
    "groq": LLMProvider(
        id="groq",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        models=(
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/qwen-2.5-32b",
        ),
    ),
    "nvidia": LLMProvider(
        id="nvidia",
        api_key_env="NVIDIA_API_KEY",
        base_url="https://integrate.api.nvidia.com/v1",
        models=(
            "nvidia_nim/deepseek-ai/deepseek-r1",
            "nvidia_nim/meta/llama-3.3-70b-instruct",
        ),
    ),
    "openrouter": LLMProvider(
        id="openrouter",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        models=(
            "openrouter/meta-llama/llama-3.3-70b-instruct",
            "openrouter/anthropic/claude-3.5-sonnet",
            "openrouter/openai/gpt-4o-mini",
        ),
    ),
    "cloudflare": LLMProvider(
        id="cloudflare",
        api_key_env="CLOUDFLARE_API_KEY",
        base_url="https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/v1",
        models=(
            "cloudflare/@cf/google/gemma-4-26b-a4b-it",
            "cloudflare/@cf/meta/llama-3.3-70b-instruct",
        ),
    ),
    "local": LLMProvider(
        id="local",
        api_key_env="LLM_API_KEY",
        base_url="http://localhost:11434/v1",
        models=(
            "openai/llama3.2",
            "openai/gpt-4o-mini",
        ),
    ),
}


def get_provider(provider_id: str) -> LLMProvider:
    """Fournisseur du registre, avec une erreur claire si l'id est inconnu."""
    if provider_id not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Fournisseur LLM inconnu : {provider_id!r}. Disponibles : {available}.")
    return PROVIDERS[provider_id]


# Types litellm "déterministes" : la classe d'exception prime sur le message.
_LITELLM_DETERMINISTIC_MARKERS: tuple[tuple[str, str], ...] = (
    ("ratelimit", "rate_limit"),
    ("authentication", "auth"),
    ("contextwindow", "context"),
    ("permissiondenied", "auth"),
    ("forbidden", "auth"),
    ("notfound", "model"),
)

# Types litellm transitoires : tentés en dernier, car leur message peut révéler
# une cause sémantique (ex. Cloudflare remonte un modèle déprécié sous forme
# d'APIConnectionError — on ne doit pas le traiter comme une panne réseau).
_LITELLM_TRANSIENT_MARKERS: tuple[str, ...] = (
    "serviceunavailable",
    "internalservererror",
    "servererror",
    "apiconnection",
    "timeout",
)

# Codes HTTP fiables (portés par les exceptions litellm / httpx / requests).
# 400 est exclu : ambigu (contexte vs modèle vs quota) → les marqueurs texte
# tranchent. ``rate_limit`` couvre aussi 402 (billing/quotas, ex. OpenRouter).
_STATUS_TO_KIND: dict[int, str] = {
    401: "auth",
    402: "rate_limit",
    403: "auth",
    404: "model",
    408: "transient",
    429: "rate_limit",
    500: "transient",
    502: "transient",
    503: "transient",
    504: "transient",
}


def _classify_error(error: Exception) -> str:
    """Classe une erreur : rate_limit, model, auth, context ou transient.

    Hiérarchie de fiabilité :
    1. type d'exception litellm déterministe (indépendant du libellé) ;
    2. marqueurs texte — ils trahissent une cause sémantique même quand le
       fournisseur la remonte comme erreur de connexion ou 5xx ;
    3. code HTTP porté par l'exception (status_code) ;
    4. types litellm transitoires (timeout, connexion, 5xx génériques).

    ``rate_limit`` couvre aussi le quota/billing (ex. OpenRouter 402 : pas
    assez de crédits) : c'est un état du compte, pas un prompt trop long —
    le vote doit continuer avec les autres fournisseurs.
    """
    cls = type(error).__name__.lower()
    for marker, kind in _LITELLM_DETERMINISTIC_MARKERS:
        if marker in cls:
            return kind

    text = str(error).lower()
    if any(
        k in text
        for k in (
            "429",
            "rate limit",
            "rate_limit",
            "quota",
            "too many requests",
            "ratelimit",
            "402",
            "credits",
            "insufficient balance",
            "insufficient_quota",
            "insufficient quota",
            "requires more credits",
            "not enough credits",
            "openrouter_credits",
            "upgrade to a paid",
            "billing",
            "payment required",
        )
    ):
        return "rate_limit"
    if any(
        k in text
        for k in (
            "context length",
            "context_length",
            "context window",
            "maximum input tokens",
            "max input tokens",
            "max_input_tokens",
            "input length exceeded",
            "maximum context",
            "exceeds the maximum",
            "prompt is too long",
            "input is too long",
            "prompt too long",
            "token count exceeds",
        )
    ):
        return "context"
    if any(
        k in text
        for k in (
            "deprecated",
            "no longer available",
            "not found",
            "not_found",
            "404",
            "model_not_found",
            "model not found",
        )
    ):
        return "model"
    if any(k in text for k in ("401", "403", "authentication", "unauthorized", "forbidden", "invalid api key", "api key")):
        return "auth"

    status = getattr(error, "status_code", None)
    if isinstance(status, int) and not isinstance(status, bool):
        kind_by_status = _STATUS_TO_KIND.get(status)
        if kind_by_status is not None:
            return kind_by_status

    if any(marker in cls for marker in _LITELLM_TRANSIENT_MARKERS):
        return "transient"
    return "transient"


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
    ) -> None:
        self._cooldown = cooldown if cooldown is not None else 30.0
        self._client_factory = client_factory or get_llm_client
        self._clock = clock or time.time
        self._configured_ids: list[str] = [
            pid.strip() for pid in (provider_ids or []) if pid.strip()
        ]

        self._providers = self._discover()
        self._health: dict[str, ProviderHealth] = {}
        self._clients: dict[str, UnifiedLLM] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ pool

    def _discover(self) -> list[LLMProvider]:
        """Construit le pool.

        - ids explicites (constructeur) : pool strict, dans cet ordre ;
        - sinon : tous les fournisseurs de ``PROVIDERS`` dont la clé d'API
          est définie.
        """
        if self._configured_ids:
            providers = [get_provider(pid) for pid in self._configured_ids]
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
                "NVIDIA_API_KEY, OPENROUTER_API_KEY, CLOUDFLARE_API_KEY, LLM_API_KEY)."
            )
        return msg

    def models_for(self, provider: LLMProvider) -> list[str]:
        """Modèle actif pour ce fournisseur (pas de fallbacks : le vote
        désigne le fournisseur, un seul modèle par fournisseur)."""
        return [provider.model()]

    def model(self) -> str:
        """Modèle du premier fournisseur du pool (affichage / métadonnées)."""
        if not self._providers:
            return "unknown"
        return self._providers[0].model()

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

    def _get_client(self, provider: LLMProvider) -> UnifiedLLM:
        with self._lock:
            client = self._clients.get(provider.id)
        if client is not None:
            return client
        kwargs: dict[str, Any] = {
            "cache_control_injection_points": [],
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
        client = self._client_factory(provider.model(), **kwargs)
        with self._lock:
            self._clients[provider.id] = client
        return client

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
        try:
            print(f"⚠ LLM {provider.id} en échec ({kind}) → exclu du vote "
                  f"pendant {self._cooldown:g}s.")
        except UnicodeEncodeError:
            # Ne jamais laisser un encodage de console casser le routage.
            print(f"LLM {provider.id} en echec ({kind}) -> cooldown.")
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
        return results[winner]

    # ------------------------------------------------------------- appel LLM

    async def acall(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Appel asynchrone : tous les fournisseurs votent, la majorité gagne."""
        now = self._clock()
        voters = [p for p in self._providers if not self._provider_is_cooling(p, now)]
        if not voters:
            # Tout est en cooldown : on retente quand même (auto-réparation).
            voters = list(self._providers)
        if not voters:
            raise RuntimeError(self._missing_keys_message())

        async def _vote(provider: LLMProvider) -> tuple[LLMProvider, Any]:
            client = self._get_client(provider)
            try:
                result = await client.acall(
                    messages, tools=tools, output_model=output_model, **kwargs
                )
                return provider, result
            except Exception as exc:  # noqa: BLE001
                return provider, exc

        outcomes = await asyncio.gather(*(_vote(p) for p in voters))

        results: dict[str, Any] = {}
        errors: list[str] = []
        for provider, outcome in outcomes:
            if isinstance(outcome, Exception):
                errors.append(self._record_failure(provider, outcome))
            else:
                results[provider.id] = outcome
                self._record_success(provider)

        if not results:
            last = errors[-1] if errors else "inconnue"
            raise RuntimeError(f"Tous les fournisseurs LLM ont échoué. Dernière erreur : {last}")
        return self._decide(results)

    def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Appel synchrone : même logique de vote que ``acall``."""
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
            "model": provider.model(),
            "base_url": provider.resolved_base_url(),
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
            "rotation": "vote",
            "cooldown_seconds": self._cooldown,
            "pool": [p.id for p in self._providers],
            "providers": [self.provider_stats(p) for p in self._providers],
        }


# ----------------------------------------------------------- singleton partagé

_ROUTER: LLMRouter | None = None


def get_router(provider_ids: list[str] | None = None) -> LLMRouter:
    """Routeur partagé (santé continue entre les runs). Créé à la demande."""
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = LLMRouter(provider_ids=provider_ids)
    return _ROUTER


def reset_router() -> None:
    """Réinitialise le singleton (tests)."""
    global _ROUTER
    _ROUTER = None


def routing_stats() -> dict[str, Any]:
    """Statistiques du routeur partagé (vide si aucun routeur créé)."""
    if _ROUTER is None:
        return {"rotation": "uninitialized", "cooldown_seconds": 0, "pool": [], "providers": []}
    return _ROUTER.routing_stats()


def build_llm(provider_ids: list[str] | None = None, fake: bool = False) -> Any:
    """Construit un client LLM : routeur multi-fournisseurs ou FakeLLMClient.

    - ``fake=True`` : FakeLLMClient scripté, sans quota (tests/développement).
    - Sinon : ``LLMRouter`` — tous les fournisseurs du pool votent à chaque
      appel (majorité + tie-break santé), cooldown simple après un échec.
    - ``provider_ids`` : pool strict optionnel (défaut : tous les fournisseurs
      dont la clé d'API est définie).
    - cache_control désactivé pour éviter l'API cachedContents (quota 0 gratuit).
    """
    # Mode fake pour tests/développement
    if fake:
        if FakeLLMClient is None:
            raise RuntimeError("FakeLLMClient non disponible (nooa<0.0.8?). Mettez à jour nooa.")
        from nooa.unifiedllm import LLMResponse

        # Helper pour créer des LLMResponse valides
        def _resp(content: str) -> LLMResponse:
            return LLMResponse(
                raw_response={"choices": [{"message": {"content": content}}]},
                content=content,
                tool_calls=[],
                finish_reason="stop",
                assistant_message={"role": "assistant", "content": content},
                reasoning=None,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

        # Note: FakeLLMClient avec scripted_responses consomme les réponses séquentiellement.
        # Pour tests de pipeline complet, préférez un vrai LLM (avec vote ci-dessous).
        # Ce mode est utile pour tests unitaires d'agents isolés.
        return FakeLLMClient(
            scripted_responses=[
                # Réponses génériques valides pour les types de retour attendus
                _resp('{"code": "import bpy\\npass", "scene_name": "test", "version": 1}'),
                _resp('{"passed": true, "score": 0.85, "issues": [], "recommendations": []}'),
                _resp('{"mood": "neutral", "music_theme": "ambient", "tempo": 120, "volume_music": 0.3, "sfx_events": [], "voice_tracks": []}'),
                _resp('{"passes": ["diffuse"], "grade": "balanced", "effects": [], "output_format": "exr"}'),
                _resp('{"language": "fr", "languages": ["fr"], "dialogues": [], "subtitles_path": "", "voice_path": "", "metadata": {}, "interface": {}}'),
            ]
        )

    # Mode réel : routeur multi-fournisseurs (vote + cooldown simple)
    return get_router(provider_ids)
