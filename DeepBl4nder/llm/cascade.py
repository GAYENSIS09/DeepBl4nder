"""Router en cascade : sélection de modèle avec escalation.

Pour chaque tâche, le router sélectionne le modèle le plus léger capable
de traiter la demande. En cas d'échec ou de qualité insuffisante,
il escalade vers un modèle plus puissant.
"""

from __future__ import annotations

import logging
from typing import Any

from DeepBl4nder.llm.classifier import TaskClassifier
from DeepBl4nder.llm.model_registry import (
    ModelCategory,
    LocalModel,
    models_for_category,
)

logger = logging.getLogger("DeepBl4nder.llm.cascade")


class CascadeRouter:
    """Route les tâches vers le modèle optimal avec escalation."""

    def __init__(self, classifier: TaskClassifier | None = None):
        self._classifier = classifier or TaskClassifier()
        self._history: list[dict[str, Any]] = []

    def classify(self, task_text: str, messages: list[dict[str, Any]] | None = None) -> ModelCategory:
        """Classe une tâche en catégorie de modèle."""
        return self._classifier.classify(task_text, messages)

    def select_model(self, category: ModelCategory) -> LocalModel:
        """Sélectionne le premier modèle disponible pour la catégorie.

        Retourne le modèle le plus léger d'abord (optimisation VRAM).
        """
        candidates = models_for_category(category)
        if not candidates:
            # Fallback: modèle général le plus léger
            candidates = models_for_category(ModelCategory.GENERAL)
        if not candidates:
            raise RuntimeError(f"Aucun modèle disponible pour la catégorie {category.value}")
        return candidates[0]

    def escalate(self, current: LocalModel, category: ModelCategory) -> LocalModel | None:
        """Passe au modèle suivant en cas d'échec.

        Retourne None si le modèle actuel est déjà le plus puissant.
        """
        candidates = models_for_category(category)
        for i, model in enumerate(candidates):
            if model.id == current.id and i + 1 < len(candidates):
                next_model = candidates[i + 1]
                logger.info(
                    "Escalade modèle : %s → %s (catégorie %s)",
                    current.id, next_model.id, category.value,
                )
                return next_model
        logger.warning(
            "Pas d'escalade possible depuis %s (catégorie %s)",
            current.id, category.value,
        )
        return None

    def select_with_escalation(
        self,
        task_text: str,
        messages: list[dict[str, Any]] | None = None,
    ) -> tuple[LocalModel, ModelCategory]:
        """Sélectionne un modèle et retourne aussi la catégorie."""
        category = self.classify(task_text, messages)
        model = self.select_model(category)
        return model, category

    def record_outcome(self, model_id: str, success: bool, quality: float | None = None) -> None:
        """Enregistre le résultat d'un appel pour optimisation future."""
        self._history.append({
            "model": model_id,
            "success": success,
            "quality": quality,
        })
        # Garder les 100 derniers résultats
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def stats(self) -> dict[str, Any]:
        """Statistiques d'utilisation des modèles."""
        if not self._history:
            return {"total": 0, "by_model": {}}
        by_model: dict[str, dict[str, Any]] = {}
        for entry in self._history:
            mid = entry["model"]
            if mid not in by_model:
                by_model[mid] = {"calls": 0, "successes": 0, "failures": 0}
            by_model[mid]["calls"] += 1
            if entry["success"]:
                by_model[mid]["successes"] += 1
            else:
                by_model[mid]["failures"] += 1
        return {"total": len(self._history), "by_model": by_model}
