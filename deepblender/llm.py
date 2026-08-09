"""Construction du client LLM (NOOA UnifiedLLM) depuis la configuration.

La sélection se fait par variables d'environnement (chargées depuis `.env`) :

- ``GEMINI_LLM_MODEL`` : modèle litellm, défaut ``gemini/gemini-3.5-flash``.
- ``GEMINI_API_KEY`` : clé Google AI Studio.
- ``DEEPBENDER_LLM_BASE_URL`` : base URL optionnelle (LLM local compatible
  OpenAI — ollama, vllm, etc.).
- ``DEEPBLENDER_FAKE_LLM`` : si "1" ou "true", utilise un FakeLLMClient pour tests
  sans appel réseau (contourne les limites de taux Gemini).
- ``GEMINI_FALLBACK_MODELS`` : liste de modèles de secours séparés par virgule
  (ex: ``gemini/gemini-2.5-flash,openai/gpt-4o-mini``).
"""

from __future__ import annotations

import os
from typing import Any

from nooa.unifiedllm import UnifiedLLM
from nooa.unifiedllm.registry import get_llm_client

# Fake client pour tests sans quota (disponible dans nooa 0.0.8+)
try:
    from nooa.unifiedllm.fake import FakeLLMClient
except ImportError:
    FakeLLMClient = None  # type: ignore[assignment,misc]

DEFAULT_MODEL = "gemini/gemini-3.5-flash"
FALLBACK_MODELS = [
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.0-flash",
]


def model_from_env() -> str:
    return os.getenv("GEMINI_LLM_MODEL", DEFAULT_MODEL)


def api_key_from_env() -> str | None:
    return os.getenv("GEMINI_API_KEY")


def fallback_models_from_env() -> list[str]:
    """Parse les modèles de secours depuis GEMINI_FALLBACK_MODELS."""
    raw = os.getenv("GEMINI_FALLBACK_MODELS", "")
    if not raw:
        return FALLBACK_MODELS
    return [m.strip() for m in raw.split(",") if m.strip()]


def use_fake_llm() -> bool:
    """Vérifie si le mode fake est activé (tests sans quota)."""
    val = os.getenv("DEEPBLENDER_FAKE_LLM", "").lower()
    return val in ("1", "true", "yes", "on")


def build_llm() -> UnifiedLLM:
    """Construit un client LLM NOOA à partir de l'environnement.

    - Mode fake : FakeLLMClient (réponses scriptées, pas de quota)
    - Mode réel : modèle principal + fallbacks si rate limit
    - cache_control désactivé pour éviter l'API cachedContents (quota 0 gratuit)
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
        # Pour tests de pipeline complet, préférez un vrai LLM (avec fallbacks ci-dessous).
        # Ce mode est utile pour tests unitaires d'agents isolés.
        return FakeLLMClient(
            scripted_responses=[
                # Réponses génériques valides pour les types de retour attendus
                _resp('{"code": "import bpy\\npass", "scene_name": "test", "version": 1}'),
                _resp('{"passed": true, "score": 0.85, "issues": [], "recommendations": []}'),
                _resp('{"mood": "neutral", "music_theme": "ambient", "tempo": 120, "volume_music": 0.3, "sfx_events": [], "voice_tracks": []}'),
                _resp('{"passes": ["diffuse"], "grade": "balanced", "effects": [], "output_format": "exr"}'),
                _resp('{"language": "fr", "dialogues": [], "subtitles_path": "", "voice_path": "", "metadata": {}, "interface": {}}'),
            ]
        )

    # Mode réel avec fallbacks
    models_to_try = [model_from_env()] + fallback_models_from_env()

    kwargs: dict[str, Any] = {"cache_control_injection_points": []}
    if api_key := api_key_from_env():
        kwargs["api_key"] = api_key
    if base_url := os.getenv("DEEPBENDER_LLM_BASE_URL"):
        kwargs["api_base"] = base_url

    last_error: Exception | None = None
    for model in models_to_try:
        try:
            return get_llm_client(model, **kwargs)
        except Exception as e:
            last_error = e
            # Si c'est une erreur de rate limit (429), on essaie le modèle suivant
            if "429" in str(e) or "rate limit" in str(e).lower() or "quota" in str(e).lower():
                print(f"⚠ Rate limit hit for {model}, trying fallback...")
                continue
            # Autre erreur : on lève
            raise

    # Tous les modèles ont échoué
    raise RuntimeError(f"All LLM models failed. Last error: {last_error}")
