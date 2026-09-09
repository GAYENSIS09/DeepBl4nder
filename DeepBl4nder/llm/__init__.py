"""Routeur LLM multi-fournisseurs (pool cloud) — remplace l'ancien routeur local.

Le registre des fournisseurs, la sélection/découverte des modèles, la
classification des erreurs et le routeur vivent dans des sous-modules dédiés
pour la maintenabilité :

- ``providers`` : registre ``PROVIDERS`` + pool configuré (env/fichier) ;
- ``selection`` : règles de sélection des modèles ; ``discovery`` : listing ;
- ``errors`` : classification des erreurs et budget crédits ;
- ``router`` : ``LLMRouter`` (vote/fallback, cooldown, santé) ;
- ``__init__`` : façade publique (ré-exports) + singleton partagé + ``build_llm``.
"""

from __future__ import annotations

import importlib
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("DeepBl4nder.llm")

# litellm imprime ses bandeaux "Give Feedback / LiteLLM.Info" hors logging :
# on coupe cette pollution console (les erreurs restent journalisées chez nous).
_litellm_module: Any = None
try:
    _litellm_module = importlib.import_module("litellm")
except Exception:  # noqa: BLE001 - litellm optionnel à l'import
    pass
if _litellm_module is not None:
    _litellm_module.suppress_debug_info = True

# Fake client pour tests sans quota (disponible dans nooa 0.0.8+)
try:
    from nooa.unifiedllm.fake import FakeLLMClient
except ImportError:
    FakeLLMClient = None  # type: ignore[assignment,misc]

from .discovery import discover_models
from .errors import _afford_cap, _classify_error
from .providers import (
    LLMProvider,
    PROVIDERS,
    configured_providers,
    get_provider,
    reset_providers_config,
    set_configured_providers,
)
from .router import LLMRouter, model_name_of
from .selection import (
    MODEL_SELECTION_RULES,
    ModelSelectionRule,
    compose_litellm_ids,
    select_models,
    selection_rule_for,
)

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


def last_decision() -> dict[str, str]:
    """Dernier fournisseur/modèle réellement utilisés (vide avant tout appel).

    Lit ``last_provider_id`` / ``last_model`` du routeur partagé sans le
    construire si aucun routeur n'existe encore. Ensemble vide = aucune
    décision réelle (routeur non créé, ou tous les fournisseurs en échec).
    """
    if _ROUTER is None:
        return {}
    provider = _ROUTER.last_provider_id
    model = _ROUTER.last_model
    if provider and model:
        return {"provider": str(provider), "model": str(model)}
    return {}


def last_attempt() -> dict[str, str]:
    """Dernière tentative (fournisseur, modèle, classe d'erreur) du routeur.

    Renseigné À CHAQUE échec — l'UI affiche la rotation/la recherche en cours
    même quand aucun fournisseur ne répond. Vide si aucun routeur créé.
    """
    if _ROUTER is None:
        return {}
    attempt = _ROUTER.last_attempt
    if attempt is None:
        return {}
    provider, model, kind = attempt
    return {"provider": str(provider), "model": str(model), "error": str(kind)}


def llm_metrics() -> dict[str, Any]:
    """Metrics LLM live agrégées (tokens, coût, latence, par agent/modèle).

    Sink in-process alimenté par le pont d'événements à chaque appel LLM ;
    sert au TUI (observabilité temps réel) et au test de l'accumulateur.
    """
    from .metrics import get_metrics

    return get_metrics().snapshot()



def build_llm(provider_ids: list[str] | None = None, fake: bool = False) -> Any:
    """Construit un client LLM : routeur multi-fournisseurs ou FakeLLMClient.

    - ``fake=True`` : FakeLLMClient scripté, sans quota (tests/développement).
    - Sinon : ``LLMRouter`` partagé — mode ``fallback`` séquentiel par défaut
      (premier fournisseur sain du pool ; ``DeepBl4nder_LLM_MODE=vote``
      restaure le vote majoritaire), cooldown simple après un échec.
    - ``provider_ids`` : pool strict optionnel (défaut : tous les fournisseurs
      dont la clé d'API est définie).
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

        return FakeLLMClient(
            scripted_responses=[
                _resp('{"code": "import bpy\\npass", "scene_name": "test", "version": 1}'),
                _resp('{"passed": true, "score": 0.85, "issues": [], "recommendations": []}'),
                _resp('{"mood": "neutral", "music_theme": "ambient", "tempo": 120, "volume_music": 0.3, "sfx_events": [], "voice_tracks": []}'),
                _resp('{"passes": ["diffuse"], "grade": "balanced", "effects": [], "output_format": "exr"}'),
                _resp('{"language": "fr", "languages": ["fr"], "dialogues": [], "subtitles_path": "", "voice_path": "", "metadata": {}, "interface": {}}'),
            ]
        )

    # Mode réel : routeur multi-fournisseurs (vote + cooldown simple)
    return get_router(provider_ids)


__all__ = [
    "LLMProvider",
    "LLMRouter",
    "MODEL_SELECTION_RULES",
    "PROVIDERS",
    "ModelSelectionRule",
    "_afford_cap",
    "_classify_error",
    "build_llm",
    "compose_litellm_ids",
    "configured_providers",
    "discover_models",
    "get_provider",
    "get_router",
    "httpx",
    "last_attempt",
    "last_decision",
    "llm_metrics",
    "model_name_of",
    "reset_providers_config",
    "reset_router",
    "routing_stats",
    "select_models",
    "selection_rule_for",
    "set_configured_providers",
]