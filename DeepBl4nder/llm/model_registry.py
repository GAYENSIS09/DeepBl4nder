"""Registre des modèles locaux avec métadonnées VRAM et catégories."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ModelCategory(Enum):
    """Catégories de modèles pour le routage par tâche."""

    FAST = "fast"          # 1.5B - routing, classification, tâches simples
    GENERAL = "general"    # 4B - chat, summarization, traduction
    CODING = "coding"      # 8B - génération de code, scripts
    REASONING = "reasoning" # 8B - analyse complexe, planification


@dataclass(frozen=True)
class LocalModel:
    """Spécification d'un modèle local GGUF."""

    id: str
    gguf_filename: str
    category: ModelCategory
    vram_gb: float
    context_window: int
    description: str
    huggingface_repo: str
    huggingface_file: str

    @property
    def gguf_path(self) -> Path:
        """Chemin complet vers le fichier GGUF."""
        models_dir = Path(os.getenv("DeepBl4nder_MODELS_DIR", "models"))
        return models_dir / self.gguf_filename


# ── Registre des modèles supportés ──────────────────────────────────────

MODELS: dict[str, LocalModel] = {
    "qwen3-4b": LocalModel(
        id="qwen3-4b",
        gguf_filename="Qwen3-4B-Q4_K_M.gguf",
        category=ModelCategory.GENERAL,
        vram_gb=3.0,
        context_window=32_768,
        description="Chat général, summarization, traduction",
        huggingface_repo="Qwen/Qwen3-4B-GGUF",
        huggingface_file="Qwen3-4B-Q4_K_M.gguf",
    ),
    "qwen3-8b": LocalModel(
        id="qwen3-8b",
        gguf_filename="Qwen3-8B-Q4_K_M.gguf",
        category=ModelCategory.CODING,
        vram_gb=5.5,
        context_window=32_768,
        description="Code generation, reasoning complexe",
        huggingface_repo="Qwen/Qwen3-8B-GGUF",
        huggingface_file="Qwen3-8B-Q4_K_M.gguf",
    ),
}

# Alias pour les catégories → modèles recommandés
CATEGORY_DEFAULTS: dict[ModelCategory, list[str]] = {
    ModelCategory.FAST: ["qwen3-4b"],
    ModelCategory.GENERAL: ["qwen3-4b", "qwen3-8b"],
    ModelCategory.CODING: ["qwen3-8b", "qwen3-4b"],
    ModelCategory.REASONING: ["qwen3-8b", "qwen3-4b"],
}


def get_model(model_id: str) -> LocalModel:
    """Récupère un modèle par son ID."""
    if model_id not in MODELS:
        available = ", ".join(sorted(MODELS))
        raise ValueError(f"Modèle inconnu : {model_id!r}. Disponibles : {available}.")
    return MODELS[model_id]


def models_for_category(category: ModelCategory) -> list[LocalModel]:
    """Retourne les modèles pour une catégorie, triés par VRAM croissante."""
    ids = CATEGORY_DEFAULTS.get(category, [ModelCategory.GENERAL.value])
    return [get_model(mid) for mid in ids if mid in MODELS]


def available_models() -> list[LocalModel]:
    """Retourne les modèles dont le fichier GGUF existe."""
    return [m for m in MODELS.values() if m.gguf_path.exists()]
