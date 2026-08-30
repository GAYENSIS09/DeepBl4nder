"""Classification heuristique des tâches pour routage de modèles.

Utilise des mots-clés et la structure des messages pour déterminer
la catégorie de modèle la plus adaptée — sans appeler de LLM.
"""

from __future__ import annotations

import re
from typing import Any

from DeepBl4nder.llm.model_registry import ModelCategory


# ── Mots-clés par catégorie (insensible à la casse) ──────────────────────

_KEYWORDS: dict[ModelCategory, tuple[str, ...]] = {
    ModelCategory.CODING: (
        "code", "script", "python", "bpy", "blender", "debug", "function",
        "import", "class", "def ", "return", "error", "traceback", "exception",
        "module", "api", "syntax", "indent", "variable", "loop", "for ",
        "while ", "if ", "else:", "try:", "except", "import bpy",
        "write_script", "build_script", "refine_script",
    ),
    ModelCategory.REASONING: (
        "analyze", "analyse", "plan", "design", "strategy", "complex",
        "evaluate", "evaluate", "compare", "pros and cons", "trade-off",
        "architecture", "approach", "why", "explain why", "reasoning",
        "step by step", "consider", "tradeoff", "optimize", "improve",
        "review", "critique", "assess",
    ),
    ModelCategory.GENERAL: (
        "chat", "summarize", "summary", "translate", "translation",
        "explain", "describe", "tell me", "what is", "how to",
        "rewrite", "paraphrase", "convert", "format", "list",
        "narrative", "story", "dialogue", "character", "scene",
        "mood", "music", "audio", "sound",
    ),
    ModelCategory.FAST: (
        "classify", "route", "detect", "check", "validate", "format",
        "yes or no", "true or false", "score", "rating", "rank",
        "priority", "urgent", "quick", "fast", "simple",
        "is it", "does it", "can it", "should",
    ),
}

# Patterns regex pour les patterns courants
_PATTERNS: dict[ModelCategory, list[re.Pattern[str]]] = {
    ModelCategory.CODING: [
        re.compile(r"\b(import\s+\w+|from\s+\w+\s+import)\b", re.IGNORECASE),
        re.compile(r"\b(def|class|async\s+def)\s+\w+", re.IGNORECASE),
        re.compile(r"\b(bpy\.\w+|bpy\.data\.\w+)", re.IGNORECASE),
    ],
    ModelCategory.REASONING: [
        re.compile(r"\b(explain\s+why|why\s+does|reasoning|step.by.step)\b", re.IGNORECASE),
        re.compile(r"\b(compare|contrast|pros?\s+and\s+cons?|trade.?off)\b", re.IGNORECASE),
    ],
    ModelCategory.FAST: [
        re.compile(r"^(yes|no|true|false|ok|validate|check)\s*$", re.IGNORECASE),
    ],
}


class TaskClassifier:
    """Classe les tâches en catégories de modèles par heuristique."""

    def classify(
        self,
        task_text: str,
        messages: list[dict[str, Any]] | None = None,
    ) -> ModelCategory:
        """Détermine la catégorie de modèle recommandée.

        Args:
            task_text: Texte de la tâche ou dernier message utilisateur.
            messages: Historique complet des messages (optionnel).

        Returns:
            ModelCategory la plus adaptée.
        """
        text = task_text.lower()
        scores: dict[ModelCategory, float] = {cat: 0.0 for cat in ModelCategory}

        # 1. Score par mots-clés
        for category, keywords in _KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[category] += 1.0

        # 2. Score par patterns regex
        for category, patterns in _PATTERNS.items():
            for pattern in patterns:
                if pattern.search(text):
                    scores[category] += 2.0  # Patterns plus discriminants

        # 3. Bonus si le dernier message est très court → FAST
        if len(text.split()) <= 5:
            scores[ModelCategory.FAST] += 1.5

        # 4. Bonus si le contexte contient du code → CODING
        if messages:
            code_indicators = 0
            for msg in messages[-3:]:  # 3 derniers messages
                content = msg.get("content", "")
                if isinstance(content, str):
                    if any(kw in content.lower() for kw in ("import bpy", "def ", "class ", "bpy.")):
                        code_indicators += 1
            if code_indicators >= 2:
                scores[ModelCategory.CODING] += 3.0

        # 5. Sélectionner la catégorie avec le meilleur score
        best_category = max(scores, key=lambda cat: scores[cat])

        # Si aucun signal clair → GENERAL par défaut
        if scores[best_category] == 0:
            return ModelCategory.GENERAL

        return best_category
