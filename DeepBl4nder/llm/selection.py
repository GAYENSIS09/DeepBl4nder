"""Sélection des modèles par fournisseur : règles, filtrage, composition litellm.

Les règles (``MODEL_SELECTION_RULES``) trient les modèles annoncés par la
découverte ``GET /models`` ; ``select_models`` applique le filtrage et
``compose_litellm_ids`` fabrique les identifiants consommeables par litellm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .providers import LLMProvider
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
        # deepseek-r1 / llama-3.x NIM : routes décommissionnées chez NVIDIA
        # (404 "Function not found for account" / 410 Gone vérifiés en direct
        # 2026-09). Catalogue 2026 : nemotron-3.5, nemotron-3, kimi, deepseek-v4.
        exclude=("deepseek-r1", "llama-3.", "yi-large", "embed", "rerank",
                 "nemoretriever", "clip", "ocr", "sdxl", "stable-diffusion",
                 "diffusion", "vila", "flux", "content-safety", "safety", "guard"),
        prefer=(
            r"nvidia/nemotron-3\.5",  # rapide et fiable (écho "OK." vérifié)
            r"nvidia/nemotron-3",
            r"moonshotai/kimi",
            r"deepseek-ai/deepseek-v4",
        ),
        max_models=3,
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
