"""Gestion robuste des fournisseurs LLM : pool multi-fournisseurs + routage.

Le registre ``PROVIDERS`` décrit chaque fournisseur via la classe
``LLMProvider`` (id, clé d'API, base URL, modèles statiques de repli).

Sélection dynamique des modèles : au démarrage du routeur, chaque fournisseur
est interrogé via sa route compatible OpenAI (``GET {base_url}/models``) ; les
identifiants annoncés sont filtrés par les règles établies
(``MODEL_SELECTION_RULES`` : exclusions embeddings/image/audio, préférences
ordonnées, quota). Tout échec de découverte retombe silencieusement sur les
listes statiques — le réseau ne doit jamais bloquer le démarrage.
``DeepBl4nder_DISCOVER_MODELS=off`` désactive la découverte.

Le ``LLMRouter`` supporte deux modes d'appel :

- ``fallback`` (défaut production via ``get_router``) : le premier fournisseur
  sain du pool répond ; on ne passe au suivant qu'en cas d'échec — un seul
  fournisseur sollicité par appel, quotas préservés ;
- ``vote`` (``DeepBl4nder_LLM_MODE=vote``) : tous les fournisseurs disponibles
  répondent en parallèle ; les réponses identiques forment une majorité →
  c'est la réponse retenue ; en cas d'égalité, la santé historique départage.

Dans les deux modes, un fournisseur en échec (429/quota, 402 crédits,
5xx, timeout, 404 modèle…) passe en ``cooldown`` et est réintégré
automatiquement quand il refroidit ; il ne participe pas aux appels suivants.

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
import logging
import os
import re
import threading
import time

import httpx

from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("DeepBl4nder.llm")

from nooa.unifiedllm import RetryConfig, UnifiedLLM
from nooa.unifiedllm.registry import get_llm_client

# litellm imprime ses bandeaux "Give Feedback / LiteLLM.Info" hors logging :
# on coupe cette pollution console (les erreurs restent journalisées chez nous).
litellm_module = None
try:
    import litellm as litellm_module

    litellm_module.suppress_debug_info = True
except Exception:  # noqa: BLE001 - litellm optionnel à l'import
    pass

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
        # Modèles vérifiés actifs sur l'API Groq (2026) — llama-3.x décommissionnés.
        models=(
            "groq/openai/gpt-oss-120b",
            "groq/qwen/qwen3.6-27b",
            "groq/groq/compound-mini",
        ),
    ),
    "nvidia": LLMProvider(
        id="nvidia",
        api_key_env="NVIDIA_API_KEY",
        base_url="https://integrate.api.nvidia.com/v1",
        # deepseek-r1 retiré : route décommissionnée chez NVIDIA — l'API
        # renvoie un 404 générique "page not found" (vérifié en direct le
        # 2026-08-22), tandis que llama-3.3-70b répond normalement.
        models=(
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


# ------------------------------------------------- sélection des modèles
#
# Les listes statiques ci-dessus servent de repli. Au démarrage du routeur,
# chaque fournisseur est interrogé (GET {base_url}/models, compatible OpenAI)
# et les modèles réellement disponibles sont filtrés par des règles
# explicites — plus aucun modèle décommissionné ne peut rester par défaut.


@dataclass(frozen=True)
class ModelSelectionRule:
    """Règles établies de sélection pour un fournisseur.

    - ``exclude`` : sous-chaînes (insensible à la casse) qui disqualifient un
      modèle (embeddings, image/vidéo/audio, garde-fous…).
    - ``prefer`` : regex ordonnées ; le premier motif qui matche fixe le rang.
      Si au moins un modèle matche, seuls ceux-là sont retenus.
    - ``max_models`` : nombre maximal de candidats conservés.
    """

    exclude: tuple[str, ...] = ()
    prefer: tuple[str, ...] = ()
    max_models: int = 4
    # Préfixes natifs à retirer avant composition de l'identifiant litellm
    # (ex. Gemini annonce "models/gemini-2.5-flash").
    strip_prefixes: tuple[str, ...] = ()


MODEL_SELECTION_RULES: dict[str, ModelSelectionRule] = {
    "gemini": ModelSelectionRule(
        exclude=("embedding", "imagen", "veo", "tts", "aqa", "learnlm", "gemma"),
        prefer=(
            r"gemini-\d+(\.\d+)?-flash(-lite)?$",  # rapide et économique d'abord
            r"gemini-\d+(\.\d+)?-flash",
            r"gemini-\d+(\.\d+)?-pro",
        ),
        max_models=4,
        strip_prefixes=("models/",),
    ),
    "groq": ModelSelectionRule(
        exclude=("whisper", "tts", "guard", "compound", "embed"),
        prefer=(r"gpt-oss-120b", r"llama-3\.3-70b-versatile", r"qwen"),
        max_models=3,
    ),
    "nvidia": ModelSelectionRule(
        # deepseek-r1 exclu : route décommissionnée (404 vérifié en direct).
        exclude=("deepseek-r1", "embed", "rerank", "nemoretriever", "clip", "ocr",
                 "sdxl", "stable-diffusion", "diffusion", "vila", "flux"),
        prefer=(r"meta/llama-3\.3-70b-instruct", r"meta/llama-3\.1-70b-instruct"),
        max_models=2,
    ),
    "openrouter": ModelSelectionRule(
        exclude=("image", "video", "embed", "vision-only", ":beta$"),
        prefer=(
            r"meta-llama/llama-3\.3-70b-instruct(:free)?$",
            r":free$",  # variantes gratuits ensuite (aucun coût crédits)
        ),
        max_models=4,
    ),
    "cloudflare": ModelSelectionRule(
        exclude=("embed", "bge", "whisper", "m2t", "m3t", "uvr", "sd-", "dreamshaper",
                 "stable-diffusion", "flux", "yolo", "resnet", "detrs", "flops", "seamless"),
        prefer=(r"@cf/meta/llama-3\.3-70b-instruct", r"@cf/google/gemma"),
        max_models=3,
    ),
    "local": ModelSelectionRule(exclude=("embed",), prefer=(), max_models=3),
}

_DEFAULT_RULE = ModelSelectionRule(
    exclude=("embed", "whisper", "tts", "rerank", "guard", "clip", "ocr",
             "stable-diffusion", "sdxl", "flux", "image-gen", "video"),
    prefer=(),
    max_models=4,
)


def selection_rule_for(provider_id: str) -> ModelSelectionRule:
    """Règles de sélection applicables à un fournisseur."""
    return MODEL_SELECTION_RULES.get(provider_id, _DEFAULT_RULE)


def _version_key(mid: str) -> tuple[int, ...]:
    """Premier numéro de version trouvé dans un id, en tuple comparable."""
    match = re.search(r"\d+(?:\.\d+)*", mid)
    if not match:
        return (0,)
    return tuple(int(part) for part in re.findall(r"\d+", match.group(0)))


def select_models(raw_ids: list[str], rule: ModelSelectionRule) -> tuple[str, ...]:
    """Applique les règles : exclusions, puis rang de préférence, puis quota.

    Au sein d'un même rang de préférence, la version la plus récente gagne
    (les listings annoncent souvent plusieurs générations ; les anciennes
    peuvent être fermées aux nouveaux comptes).
    """
    kept = [
        mid for mid in raw_ids
        if not any(marker.lower() in mid.lower() for marker in rule.exclude)
    ]
    if rule.strip_prefixes:
        stripped = []
        for mid in kept:
            for prefix in rule.strip_prefixes:
                if mid.startswith(prefix):
                    mid = mid[len(prefix):]
                    break
            if mid not in stripped:
                stripped.append(mid)
        kept = stripped
    if rule.prefer:

        def rank(mid: str) -> int:
            for index, pattern in enumerate(rule.prefer):
                if re.search(pattern, mid, re.IGNORECASE):
                    return index
            return len(rule.prefer)

        matching = [mid for mid in kept if rank(mid) < len(rule.prefer)]
        if matching:
            matching.sort(
                key=lambda mid: (
                    rank(mid),
                    tuple(-part for part in _version_key(mid)),
                    mid,
                )
            )
            kept = matching
    return tuple(kept[: rule.max_models])


def _litellm_prefix(provider: LLMProvider) -> str:
    """Préfixe litellm du fournisseur, déduit de son modèle statique.

    Ex. ``nvidia_nim/meta/llama-3.3-70b-instruct`` → ``nvidia_nim`` ; sans
    préfixe (id local nu), litellm route en OpenAI-compatible → ``openai``.
    """
    static = provider.default_model()
    return static.split("/", 1)[0] if "/" in static else "openai"


def compose_litellm_ids(
    provider: LLMProvider,
    native_ids: tuple[str, ...],
    rule: ModelSelectionRule,
) -> tuple[str, ...]:
    """Convertit les identifiants natifs du fournisseur au format litellm."""
    prefix = _litellm_prefix(provider)
    composed: list[str] = []
    for native in native_ids:
        mid = native
        for strip in rule.strip_prefixes:
            if mid.startswith(strip):
                mid = mid[len(strip):]
                break
        litellm_id = f"{prefix}/{mid}"
        if litellm_id not in composed:
            composed.append(litellm_id)
    return tuple(composed)


# Routes de listing par fournisseur : (suffixe, clé du tableau, champ id).
# La plupart exposent GET /models compatible OpenAI. Préfixe spécial
# ``ROOT:`` = chemin relatif à la racine API (base amputée de « /ai/v1 ») :
# le listing Cloudflare vit sous /client/v4/accounts/{id}/ai/models/search,
# alors que GET …/ai/v1/models répond 405.
_DISCOVERY_ROUTES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "cloudflare": (
        ("ROOT:/ai/models/search", "result", "name"),
        ("/models", "data", "id"),
    ),
}
_DEFAULT_DISCOVERY_ROUTE = (("/models", "data", "id"),)


def discover_models(provider: LLMProvider, timeout: float = 6.0) -> tuple[str, ...] | None:
    """Liste brute des modèles annoncés par le fournisseur.

    Essaie les routes de listing connues (compatible OpenAI en général,
    ``/ai/models/search`` pour Cloudflare). Retourne ``None`` en cas d'échec
    (réseau, clé, format) — jamais d'exception : la liste statique reste le
    filet de sécurité.
    """
    base = provider.resolved_base_url().rstrip("/")
    api_root = re.sub(r"/ai/v1$", "", base)
    headers: dict[str, str] = {}
    api_key = provider.api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    routes = _DISCOVERY_ROUTES.get(provider.id, _DEFAULT_DISCOVERY_ROUTE)
    last_error: Exception | None = None
    for suffix, collection_key, id_field in routes:
        if suffix.startswith("ROOT:"):
            url = f"{api_root}{suffix[len('ROOT:'):]}"
        else:
            url = f"{base}{suffix}"
        try:
            response = httpx.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - on essaie la route suivante
            last_error = exc
            logger.debug("Listing %s via %s impossible (%s)", provider.id, url, exc)
            continue
        items = payload.get(collection_key, [])
        ids = [
            str(item.get(id_field))
            for item in items
            if isinstance(item, dict) and item.get(id_field)
        ]
        logger.debug("Modèles bruts %s via %s (%d) : %s", provider.id, suffix, len(ids), ids)
        if ids:
            return tuple(ids)
    if last_error is not None:
        logger.warning(
            "Découverte des modèles %s impossible (%s : %s) → liste statique.",
            provider.id,
            type(last_error).__name__,
            str(last_error)[:160],
        )
    return None


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
            # Quotas quotidiens/mensuels Cloudflare Workers AI : le fournisseur
            # les remonte enveloppés dans une APIConnectionError ("… used up
            # your daily free allocation of 10,000 neurons …") — c'est un état
            # du compte, pas une panne réseau.
            "free allocation",
            "neurons",
            "workers paid plan",
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


# Repli « budget crédits » : OpenRouter (entre autres) refuse une requête
# quand ``max_tokens`` dépasse ce que le solde peut couvrir — "You requested
# up to N tokens, but can only afford M." Plutôt que d'exclure un fournisseur
# sain, on retente UNE fois avec max_tokens=M. En dessous de
# ``_MIN_DOWNGRADE_TOKENS``, la sortie serait tronquée au point de produire du
# contenu invalide : on abandonne le fournisseur.
_AFFORD_RE = re.compile(r"can only afford (\d+)")
_MIN_DOWNGRADE_TOKENS = 1024


def _afford_cap(error: Exception) -> int | None:
    """Plafond de complétion annoncable par le fournisseur, sinon None."""
    if _classify_error(error) != "rate_limit":
        return None
    match = _AFFORD_RE.search(str(error).lower())
    return int(match.group(1)) if match else None


async def _acall_with_budget_retry(
    client: UnifiedLLM,
    messages: list[dict[str, Any]],
    tools: list[Any] | None,
    output_model: type[Any] | None,
    kwargs: dict[str, Any],
) -> tuple[Any, bool]:
    """Appel client avec repli budget : retourne (résultat, repli_effectué).

    Si l'appel échoue parce que le plafond de crédits est dépassé et que le
    plafond annoncé reste exploitable, retente une seule fois avec
    ``max_tokens`` réduit ; sinon relève l'erreur d'origine.
    """
    try:
        result = await client.acall(messages, tools=tools, output_model=output_model, **kwargs)
        return result, False
    except Exception as exc:  # noqa: BLE001
        cap = _afford_cap(exc)
        requested = kwargs.get("max_tokens")
        if (
            cap is not None
            and isinstance(requested, int)
            and not isinstance(requested, bool)
            and requested > cap >= _MIN_DOWNGRADE_TOKENS
        ):
            logger.warning(
                "LLM : max_tokens=%d refusé (budget crédits ≤ %d) → nouvelle tentative à max_tokens=%d",
                requested,
                cap,
                cap,
            )
            result = await client.acall(
                messages, tools=tools, output_model=output_model, **{**kwargs, "max_tokens": cap}
            )
            return result, True
        raise


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


# ----------------------------------------------------------- singleton partagé

_ROUTER: LLMRouter | None = None


def get_router(provider_ids: list[str] | None = None) -> LLMRouter:
    """Routeur partagé (santé continue entre les runs). Créé à la demande.

    Voie production : mode ``fallback`` séquentiel par défaut (quotas
    préservés). ``DeepBl4nder_LLM_MODE=vote`` restaure le vote multi-LLM.
    """
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = LLMRouter(
            provider_ids=provider_ids,
            mode=os.environ.get("DeepBl4nder_LLM_MODE", "fallback"),
        )
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
    - Sinon : ``LLMRouter`` partagé — mode ``fallback`` séquentiel par défaut
      (premier fournisseur sain du pool ; ``DeepBl4nder_LLM_MODE=vote``
      restaure le vote majoritaire), cooldown simple après un échec.
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
