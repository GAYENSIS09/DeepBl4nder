"""Gestion robuste des fournisseurs LLM : pool multi-fournisseurs + failover.

Un registre ``PROVIDERS`` décrit chaque fournisseur (clé d'API, base URL et
modèles disponibles). Contrairement à un système mono-fournisseur, le
``LLMRouter`` utilise TOUS les fournisseurs configurés pour :

- répartir les appels en ``random`` (tirage uniforme) ou ``adaptive`` (pondéré
  par la santé historique) → moins de rate limits ;
- basculer automatiquement sur un autre fournisseur en cas d'erreur (429,
  5xx, timeout, 404 modèle…) ;
- mettre un fournisseur en ``cooldown`` après un échec (durée dépendante du
  type d'erreur) et le réintégrer tout seul quand il refroidit.

Configuration via ``.env`` :

- ``LLM_PROVIDERS`` : liste ordonnée d'ids de fournisseurs (séparés par
  virgule). Par défaut : tous les fournisseurs dont la clé dédiée est définie.
- ``LLM_PROVIDER`` : fournisseur préféré (mis en tête de pool ; rétrocompat).
- ``LLM_ROTATION`` : ``adaptive`` (défaut — tirage pondéré par le taux de
  réussite historique de chaque fournisseur) ou ``random`` (tirage uniforme à
  chaque appel).
- ``LLM_COOLDOWN_SECONDS`` : cooldown de base après un échec (défaut 30 s ;
  ×5 pour rate limit, ×10 pour erreurs d'auth/modèle).
- ``LLM_MODEL`` / ``<FOURNISSEUR>_MODEL`` : modèle actif par fournisseur
  (pas de modèles de secours : le routeur bascule de fournisseur).

Variables héritées toujours supportées : ``GEMINI_LLM_MODEL``,
``DEEPBLENDER_LLM_BASE_URL``, ``DEEPBLENDER_FAKE_LLM`` (mode fake pour les
tests sans quota).
"""

from __future__ import annotations

import os
import random
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
    """Fournisseur LLM : clé d'API, base URL officielle et modèles disponibles."""

    id: str
    api_key_env: str
    base_url: str
    models: tuple[str, ...]

    def default_model(self) -> str:
        """Premier modèle disponible (utilisé si rien n'est configuré)."""
        return self.models[0]


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

# Compatibilité : ancien nom (id fournisseur -> modèles disponibles).
MODELS_DICT: dict[str, list[str]] = {pid: list(p.models) for pid, p in PROVIDERS.items()}

DEFAULT_PROVIDER = "gemini"

_ROTATIONS = ("random", "adaptive")


def _weighted_shuffle(items: list[Any], weights: list[float], rng: random.Random | Any) -> list[Any]:
    """Tri aléatoire pondéré (sans remise).

    Les éléments à poids élevé sortent plus souvent en tête, sans jamais
    exclure totalement les autres — utile pour "sonder" un fournisseur en
    délicatesse plutôt que de l'abandonner définitivement.
    """
    pool = list(zip(items, weights))
    result: list[Any] = []
    while pool:
        total = sum(w for _, w in pool)
        r = rng.uniform(0, total)
        upto = 0.0
        for i, (item, w) in enumerate(pool):
            upto += w
            if upto >= r:
                result.append(item)
                pool.pop(i)
                break
    return result


def provider_from_env() -> str:
    """Id du fournisseur actif (``LLM_PROVIDER``, défaut ``gemini``)."""
    return os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)


def get_provider(provider_id: str | None = None) -> LLMProvider:
    """Retourne le fournisseur demandé, sinon celui de l'environnement."""
    pid = provider_id or provider_from_env()
    if pid not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Fournisseur LLM inconnu : {pid!r}. Disponibles : {available}.")
    return PROVIDERS[pid]


def model_from_env(provider: LLMProvider | None = None) -> str:
    """Modèle actif : ``LLM_MODEL``, puis ``<FOURNISSEUR>_MODEL``, puis défaut."""
    prov = provider or get_provider()
    for env_name in ("LLM_MODEL", f"{prov.id.upper()}_MODEL"):
        if explicit := os.getenv(env_name):
            return explicit
    if prov.id == "gemini":
        legacy = os.getenv("GEMINI_LLM_MODEL")
        if legacy:
            return legacy
    return prov.default_model()


def api_key_from_env(provider: LLMProvider | None = None) -> str | None:
    """Clé d'API : ``LLM_API_KEY`` surchargée, sinon la clé dédiée du fournisseur."""
    prov = provider or get_provider()
    return os.getenv("LLM_API_KEY") or os.getenv(prov.api_key_env)


def api_base_from_env(provider: LLMProvider | None = None) -> str | None:
    """Base URL : surcharge explicite, sinon la base par défaut pour les locaux."""
    prov = provider or get_provider()
    custom = os.getenv("LLM_BASE_URL") or os.getenv("DEEPBLENDER_LLM_BASE_URL")
    if custom:
        return custom
    if prov.id == "local":
        return prov.base_url
    return None


def resolved_base_url(provider: LLMProvider | None = None) -> str:
    """Base URL effective, placeholders substitués (ex. ``ACCOUNT_ID`` cloudflare).

    Cloudflare exige l'identifiant de compte dans l'URL ; litellm le lit
    aussi à l'appel via ``CLOUDFLARE_ACCOUNT_ID``, cette fonction sert à
    l'affichage (config / stats) sans placeholder brut.
    """
    prov = provider or get_provider()
    custom = api_base_from_env(prov)
    if custom:
        return custom
    if "ACCOUNT_ID" in prov.base_url:
        return prov.base_url.replace("ACCOUNT_ID", os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
    return prov.base_url


def use_fake_llm() -> bool:
    """Vérifie si le mode fake est activé (tests sans quota)."""
    val = os.getenv("DEEPBLENDER_FAKE_LLM", "").lower()
    return val in ("1", "true", "yes", "on")


def provider_config(provider: LLMProvider | None = None) -> dict[str, Any]:
    """Résumé de configuration d'un fournisseur (sans exposer la clé)."""
    prov = provider or get_provider()
    return {
        "id": prov.id,
        "base_url": resolved_base_url(prov),
        "model": model_from_env(prov),
        "api_key_configured": bool(api_key_from_env(prov)),
    }


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
    le failover doit continuer.
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
        kind = _STATUS_TO_KIND.get(status)
        if kind is not None:
            return kind

    if any(marker in cls for marker in _LITELLM_TRANSIENT_MARKERS):
        return "transient"
    return "transient"


_COOLDOWN_FACTORS: dict[str, int] = {"rate_limit": 5, "model": 10, "auth": 10}


@dataclass
class ProviderHealth:
    """Santé d'un couple (fournisseur, modèle) : compteurs, cooldown, erreur."""

    successes: int = 0
    failures: int = 0
    cooldown_until: float = 0.0
    last_error: str | None = None

    def is_cooling(self, now: float) -> bool:
        return self.cooldown_until > now


class LLMRouter:
    """Routeur multi-fournisseurs : rotation configurable + failover + cooldown.

    Rotation : ``adaptive`` (défaut, pondéré par la santé historique de chaque
    fournisseur) ou ``random`` (tirage uniforme). Compatible drop-in avec
    ``UnifiedLLM`` (``call`` / ``acall``) donc directement injectable dans les
    agents NOOA.
    """

    def __init__(
        self,
        provider_ids: list[str] | None = None,
        rotation: str | None = None,
        cooldown: float | None = None,
        client_factory: Callable[..., UnifiedLLM] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._rotation = (rotation or os.getenv("LLM_ROTATION", "adaptive")).strip().lower()
        if self._rotation not in _ROTATIONS:
            self._rotation = "adaptive"
        self._cooldown = cooldown if cooldown is not None else float(
            os.getenv("LLM_COOLDOWN_SECONDS", "30") or "30"
        )
        self._client_factory = client_factory or get_llm_client
        self._clock = clock or time.time
        self._configured_ids: list[str] = provider_ids or []

        self._providers = self._discover()
        self._health: dict[tuple[str, str], ProviderHealth] = {}
        self._clients: dict[tuple[str, str], UnifiedLLM] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ pool

    def _available(self, provider: LLMProvider) -> bool:
        """Un fournisseur est utilisable s'il a sa clé dédiée.

        ``local`` n'est utilisable que si ``LLM_API_KEY`` est définie (serveur
        compatible OpenAI), pour ne pas tenter un serveur absent à chaque appel.
        """
        return bool(os.getenv(provider.api_key_env))

    def _discover(self) -> list[LLMProvider]:
        """Construit le pool.

        Ordre de priorité :
        - ids explicites (constructeur) ou ``LLM_PROVIDERS`` : pool strict,
          aucun fournisseur ajouté automatiquement ;
        - ``LLM_PROVIDER`` : ce fournisseur en tête + tous les autres configurés ;
        - sinon : tous les fournisseurs configurés (clé dédiée définie).
        """
        strict = False
        if self._configured_ids:
            raw_ids = [pid.strip() for pid in self._configured_ids if pid.strip()]
            strict = True
        elif providers_env := os.getenv("LLM_PROVIDERS"):
            raw_ids = [pid.strip() for pid in providers_env.split(",") if pid.strip()]
            strict = True
        elif primary := os.getenv("LLM_PROVIDER"):
            raw_ids = [primary]
        else:
            raw_ids = []

        if raw_ids:
            self._configured_ids = raw_ids
            providers = [get_provider(pid) for pid in raw_ids]
            if strict:
                return [p for p in providers if self._available(p)]
            providers = providers + [
                p
                for p in PROVIDERS.values()
                if p.id not in {x.id for x in providers} and self._available(p)
            ]
        else:
            providers = [p for p in PROVIDERS.values() if self._available(p)]

        pool = [p for p in providers if self._available(p)]
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
            msg += f" Vérifiez les clés suivantes dans .env : {keys} (ou LLM_API_KEY)."
        else:
            msg += (
                " Définissez au moins une clé d'API (GEMINI_API_KEY, GROQ_API_KEY, "
                "NVIDIA_API_KEY, OPENROUTER_API_KEY, CLOUDFLARE_API_KEY) ou LLM_PROVIDERS."
            )
        msg += " Pour le mode sans quota : DEEPBLENDER_FAKE_LLM=1."
        return msg

    def models_for(self, provider: LLMProvider) -> list[str]:
        """Modèle actif pour ce fournisseur (pas de fallbacks : le routeur
        bascule de fournisseur plutôt que de modèle)."""
        model = model_from_env(provider)
        return [model] if model else []

    def providers(self) -> list[LLMProvider]:
        return list(self._providers)

    @property
    def rotation(self) -> str:
        return self._rotation

    # -------------------------------------------------------------- routing

    def _health_for(self, provider_id: str, model: str) -> ProviderHealth:
        """Santé d'un couple (fournisseur, modèle) — créée à la volée."""
        key = (provider_id, model)
        with self._lock:
            health = self._health.get(key)
            if health is None:
                health = ProviderHealth()
                self._health[key] = health
        return health

    def _provider_models_health(self, provider: LLMProvider) -> list[ProviderHealth]:
        """Santé de tous les modèles d'un fournisseur (vue agrégée)."""
        return [self._health_for(provider.id, m) for m in self.models_for(provider)]

    def _provider_is_cooling(self, provider: LLMProvider, now: float) -> bool:
        """Un fournisseur n'est 'en cooldown' que si TOUS ses modèles le sont."""
        healths = self._provider_models_health(provider)
        return bool(healths) and all(h.is_cooling(now) for h in healths)

    def _provider_cooldown_until(self, provider: LLMProvider) -> float:
        healths = self._provider_models_health(provider)
        return min((h.cooldown_until for h in healths), default=0.0)

    def _provider_weight(self, provider: LLMProvider) -> float:
        """Poids adaptatif d'un fournisseur : taux de réussite agrégé + 5 %."""
        successes = sum(h.successes for h in self._provider_models_health(provider))
        failures = sum(h.failures for h in self._provider_models_health(provider))
        total = successes + failures
        return 1.0 if total == 0 else 0.05 + (successes / total)

    def _ordered_candidates(self, now: float) -> list[LLMProvider]:
        """Fournisseurs à essayer pour un appel, selon la stratégie."""
        with self._lock:
            order = list(self._providers)
        if self._rotation == "random":
            order = order.copy()
            random.shuffle(order)
        else:  # adaptive
            order = _weighted_shuffle(
                order, [self._provider_weight(p) for p in order], random
            )

        cooling = [p for p in order if self._provider_is_cooling(p, now)]
        healthy = [p for p in order if not self._provider_is_cooling(p, now)]
        if healthy:
            return healthy
        # Tout est en cooldown : on réessaie le plus proche de l'expiration
        # (auto-réparation) plutôt que d'échouer sans appel.
        if cooling:
            return [min(cooling, key=self._provider_cooldown_until)]
        return order

    def _ordered_models(self, provider: LLMProvider, now: float) -> list[str]:
        """Ordre des modèles à essayer pour ce fournisseur, selon la stratégie.

        Un seul modèle actif par fournisseur (pas de fallbacks) : les modèles
        en cooldown passent après les sains ; si tous refroidissent, on
        réessaie le plus proche de l'expiration.
        """
        models = self.models_for(provider)
        if self._rotation == "random":
            models = models.copy()
            random.shuffle(models)
        elif self._rotation == "adaptive":
            def _model_weight(model: str) -> float:
                h = self._health_for(provider.id, model)
                total = h.successes + h.failures
                return 1.0 if total == 0 else 0.05 + (h.successes / total)

            models = _weighted_shuffle(models, [_model_weight(m) for m in models], random)

        cooling = [m for m in models if self._health_for(provider.id, m).is_cooling(now)]
        healthy = [m for m in models if not self._health_for(provider.id, m).is_cooling(now)]
        if healthy:
            return healthy
        if cooling:
            return [min(cooling, key=lambda m: self._health_for(provider.id, m).cooldown_until)]
        return models

    def _get_client(self, provider: LLMProvider, model: str) -> UnifiedLLM:
        key = (provider.id, model)
        with self._lock:
            client = self._clients.get(key)
        if client is not None:
            return client
        api_key = api_key_from_env(provider)
        kwargs: dict[str, Any] = {
            "cache_control_injection_points": [],
            # Fail fast : le routeur gère lui-même le failover et le cooldown
            # par fournisseur. Un seul retry court pour les erreurs transitoires,
            # aucun backoff long sur rate limit (sinon un 429 bloque le run ~3 min
            # et chaque tentative consomme des tokens inutilement).
            "retry_config": RetryConfig(
                max_retries=1,
                base_delay=1.0,
                rate_limit_extra_retries=0,
                rate_limit_base_delay=1.0,
            ),
        }
        if api_key:
            kwargs["api_key"] = api_key
        if api_base := api_base_from_env(provider):
            kwargs["api_base"] = api_base
        client = self._client_factory(model, **kwargs)
        with self._lock:
            self._clients[key] = client
        return client

    def _record_success(self, provider: LLMProvider, model: str) -> None:
        health = self._health_for(provider.id, model)
        with self._lock:
            health.successes += 1
            health.cooldown_until = 0.0
            health.last_error = None

    def _record_failure(self, provider: LLMProvider, model: str, error: Exception) -> str:
        kind = _classify_error(error)
        now = self._clock()
        health = self._health_for(provider.id, model)
        with self._lock:
            health.failures += 1
            health.last_error = str(error)[:500]
            factor = _COOLDOWN_FACTORS.get(kind, 1)
            health.cooldown_until = now + self._cooldown * factor
        try:
            if kind == "context":
                print(f"⚠ LLM {provider.id}/{model} en échec ({kind}) : prompt trop long → pas de bascule utile.")
            else:
                print(f"⚠ LLM {provider.id}/{model} en échec ({kind}) → bascule vers un autre fournisseur.")
        except UnicodeEncodeError:
            # Ne jamais laisser un encodage de console casser le failover.
            print(f"LLM {provider.id}/{model} en echec ({kind}) -> bascule.")
        return str(error)

    # ------------------------------------------------------------- appel LLM

    def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Appel synchrone avec failover multi-fournisseurs."""
        last_error = "aucune erreur capturée"
        now = self._clock()
        for provider in self._ordered_candidates(now):
            for model in self._ordered_models(provider, now):
                client = self._get_client(provider, model)
                try:
                    result = client.call(messages, tools=tools, output_model=output_model, **kwargs)
                    self._record_success(provider, model)
                    return result
                except Exception as exc:  # noqa: BLE001
                    last_error = self._record_failure(provider, model, exc)
                    if _classify_error(exc) == "context":
                        # Un prompt trop long est déterministe : changer de
                        # fournisseur ne fait que brûler du quota. On arrête.
                        raise RuntimeError(
                            "Prompt trop long : la fenêtre de contexte du modèle "
                            f"{provider.id}/{model} est dépassée. Réduisez le brief "
                            "ou la taille du contexte, ou utilisez un modèle avec une "
                            f"fenêtre plus grande. Détail : {last_error}"
                        ) from exc
        raise RuntimeError(f"Tous les fournisseurs LLM ont échoué. Dernière erreur : {last_error}")

    async def acall(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Appel asynchrone avec failover multi-fournisseurs."""
        last_error = "aucune erreur capturée"
        now = self._clock()
        for provider in self._ordered_candidates(now):
            for model in self._ordered_models(provider, now):
                client = self._get_client(provider, model)
                try:
                    result = await client.acall(
                        messages, tools=tools, output_model=output_model, **kwargs
                    )
                    self._record_success(provider, model)
                    return result
                except Exception as exc:  # noqa: BLE001
                    last_error = self._record_failure(provider, model, exc)
                    if _classify_error(exc) == "context":
                        # Un prompt trop long est déterministe : changer de
                        # fournisseur ne fait que brûler du quota. On arrête.
                        raise RuntimeError(
                            "Prompt trop long : la fenêtre de contexte du modèle "
                            f"{provider.id}/{model} est dépassée. Réduisez le brief "
                            "ou la taille du contexte, ou utilisez un modèle avec une "
                            f"fenêtre plus grande. Détail : {last_error}"
                        ) from exc
        raise RuntimeError(f"Tous les fournisseurs LLM ont échoué. Dernière erreur : {last_error}")

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
        model_stats = []
        for model in self.models_for(provider):
            h = self._health_for(provider.id, model)
            model_stats.append(
                {
                    "model": model,
                    "successes": h.successes,
                    "failures": h.failures,
                    "cooldown_remaining_s": max(0.0, h.cooldown_until - now),
                    "last_error": h.last_error,
                }
            )
        return {
            "id": provider.id,
            "model": model_from_env(provider),
            "base_url": resolved_base_url(provider),
            "models": model_stats,
            "successes": sum(m["successes"] for m in model_stats),
            "failures": sum(m["failures"] for m in model_stats),
            "cooldown_remaining_s": max(0.0, self._provider_cooldown_until(provider) - now),
            "last_error": next(
                (m["last_error"] for m in model_stats if m["last_error"]), None
            ),
        }

    def routing_stats(self) -> dict[str, Any]:
        """Résumé observable du routeur (santé par fournisseur, sans clés)."""
        return {
            "rotation": self._rotation,
            "cooldown_seconds": self._cooldown,
            "pool": [p.id for p in self._providers],
            "providers": [self.provider_stats(p) for p in self._providers],
        }


# ----------------------------------------------------------- singleton partagé

_ROUTER: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Routeur partagé (santé continue entre les runs). Créé à la demande."""
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = LLMRouter()
    return _ROUTER


def reset_router() -> None:
    """Réinitialise le singleton (tests / relecture du .env)."""
    global _ROUTER
    _ROUTER = None


def routing_stats() -> dict[str, Any]:
    """Statistiques du routeur partagé (vide si aucun routeur créé)."""
    if _ROUTER is None:
        return {"rotation": "uninitialized", "cooldown_seconds": 0, "pool": [], "providers": []}
    return _ROUTER.routing_stats()


def build_llm() -> Any:
    """Construit un client LLM robuste (mode fake ou routeur multi-fournisseurs).

    - Mode fake (``DEEPBLENDER_FAKE_LLM``) : FakeLLMClient scripté, sans quota.
    - Mode réel : ``LLMRouter`` — utilise tous les fournisseurs configurés avec
      rotation random/adaptive + failover + cooldown (robuste au rate limiting).
    - cache_control désactivé pour éviter l'API cachedContents (quota 0 gratuit).
    """
    # Mode fake pour tests/développement
    if use_fake_llm():
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
        # Pour tests de pipeline complet, préférez un vrai LLM (avec failover ci-dessous).
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

    # Mode réel : routeur multi-fournisseurs (random/adaptive + failover + cooldown)
    return get_router()
