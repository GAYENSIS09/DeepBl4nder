"""Context Pruner : nettoyage et optimisation du contexte avant injection LLM.

Étape 1 du pipeline de gestion de contexte avancée.
Réduit les tokens en éliminant les redondances et en appliquant des budgets par type.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


# Budgets tokens par type de bloc contextuel
DEFAULT_BUDGETS: dict[str, int] = {
    "system_prompt": 3000,
    "available_skills": 800,
    "skill_*": 1200,      # max par skill individuel
    "domain_schema": 600,
    "brief": 400,
    "dynamic": 500,
    "history": 2000,
    "default": 500,
}

# Patterns de clés pour appliquer les budgets
_SKILL_PATTERN = re.compile(r"^skill_")
_BUDGET_KEY_MAP = {
    "system_prompt": ["system_prompt"],
    "available_skills": ["available_skills"],
    "domain_schema": ["domain_schema"],
    "brief": ["brief"],
    "dynamic": ["scene_summary", "render_summary"],
    "history": ["conversation_history"],
}


@dataclass
class PrunedBlock:
    """Un bloc de contexte après nettoyage."""
    key: str
    value: str
    prefix: bool
    original_tokens: int
    pruned_tokens: int
    truncated: bool = False


@dataclass
class PruneResult:
    """Résultat complet du pruning de contexte."""
    blocks: list[PrunedBlock] = field(default_factory=list)
    total_original_tokens: int = 0
    total_pruned_tokens: int = 0
    duplicates_removed: int = 0

    @property
    def savings_percent(self) -> float:
        if self.total_original_tokens == 0:
            return 0.0
        return (1 - self.total_pruned_tokens / self.total_original_tokens) * 100

    @property
    def tokens_saved(self) -> int:
        return self.total_original_tokens - self.total_pruned_tokens


class ContextPruner:
    """Étape 1: Nettoyage et déduplication du contexte.

    Fonctionnalités:
    - Suppression des doublons par hash de contenu
    - Tronquage selon les budgets tokens par type
    - Élimination des valeurs vides
    - Gestion intelligente du prefix vs suffix
    """

    def __init__(self, budgets: dict[str, int] | None = None) -> None:
        self._budgets = budgets or DEFAULT_BUDGETS.copy()

    def _estimate_tokens(self, text: str) -> int:
        """Estime le nombre de tokens (approximation 1 token ≈ 4 chars)."""
        return len(text) // 4 if text else 0

    def _get_budget(self, key: str) -> int:
        """Retourne le budget tokens pour une clé donnée."""
        # Match skill_* pattern
        if _SKILL_PATTERN.match(key):
            return self._budgets.get("skill_*", 1200)

        # Match known key patterns
        for budget_name, keys in _BUDGET_KEY_MAP.items():
            if key in keys:
                return self._budgets.get(budget_name, 500)

        return self._budgets.get("default", 500)

    def _content_hash(self, value: str) -> str:
        """Hash du contenu pour détection de doublons."""
        return hashlib.md5(value.encode("utf-8")).hexdigest()[:12]

    def _truncate_to_budget(self, text: str, budget: int) -> tuple[str, bool]:
        """Tronque le texte au budget tokens. Retourne (texte, a_été_tronqué)."""
        token_estimate = self._estimate_tokens(text)
        if token_estimate <= budget:
            return text, False

        # Calculer le nombre de chars à garder (budget * 4)
        char_limit = budget * 4
        # Couper proprement au dernier espace/point
        truncated = text[:char_limit]
        last_space = truncated.rfind(" ")
        last_period = truncated.rfind(".")
        cut_point = max(last_space, last_period)
        if cut_point > char_limit * 0.8:
            truncated = truncated[:cut_point + 1]

        return truncated + "...", True

    def prune(self, context: dict[str, Any]) -> PruneResult:
        """Nettoie et optimise le contexte.

        Args:
            context: Dict des contextes (clé → Context ou valeur).

        Returns:
            PruneResult avec les blocs nettoyés et les métriques.
        """
        result = PruneResult()
        seen_hashes: dict[str, str] = {}

        for key, ctx in context.items():
            # Extraire la valeur
            if hasattr(ctx, "value"):
                value = ctx.value or ""
                prefix = getattr(ctx, "prefix", True)
            elif isinstance(ctx, str):
                value = ctx
                prefix = True
            else:
                continue

            # Étape 1: Supprimer les valeurs vides
            if not value or not value.strip():
                continue

            original_tokens = self._estimate_tokens(value)

            # Étape 2: Détection de doublons
            content_hash = self._content_hash(value)
            if content_hash in seen_hashes:
                result.duplicates_removed += 1
                continue
            seen_hashes[content_hash] = key

            # Étape 3: Tronquage selon le budget
            budget = self._get_budget(key)
            pruned_value, truncated = self._truncate_to_budget(value, budget)
            pruned_tokens = self._estimate_tokens(pruned_value)

            result.blocks.append(PrunedBlock(
                key=key,
                value=pruned_value,
                prefix=prefix,
                original_tokens=original_tokens,
                pruned_tokens=pruned_tokens,
                truncated=truncated,
            ))

            result.total_original_tokens += original_tokens
            result.total_pruned_tokens += pruned_tokens

        return result

    def prune_skills(self, summaries: list[str], budget: int = 800) -> str:
        """Version spécialisée pour les résumés de skills.

        Args:
            summaries: Liste des résumés de skills.
            budget: Budget total en tokens pour tous les résumés.

        Returns:
            Texte des résumés optimisé.
        """
        if not summaries:
            return ""

        # Dédupliquer par contenu
        seen = set()
        unique_summaries = []
        for s in summaries:
            h = self._content_hash(s)
            if h not in seen:
                seen.add(h)
                unique_summaries.append(s)

        # Trier par longueur (les plus courts d'abord = plus d'infos dans le budget)
        unique_summaries.sort(key=len)

        result_parts = []
        current_tokens = 0

        for summary in unique_summaries:
            tokens = self._estimate_tokens(summary)
            if current_tokens + tokens > budget:
                # Essayer de tronquer le dernier
                remaining = budget - current_tokens
                if remaining > 50:  # Au moins 50 tokens utiles
                    truncated, _ = self._truncate_to_budget(summary, remaining)
                    result_parts.append(truncated)
                break
            result_parts.append(summary)
            current_tokens += tokens

        return "\n".join(result_parts)

    def get_metrics(self, result: PruneResult) -> dict[str, Any]:
        """Retourne les métriques de pruning formatées."""
        return {
            "total_blocks": len(result.blocks),
            "duplicates_removed": result.duplicates_removed,
            "tokens_original": result.total_original_tokens,
            "tokens_pruned": result.total_pruned_tokens,
            "tokens_saved": result.tokens_saved,
            "savings_percent": round(result.savings_percent, 1),
            "truncated_blocks": sum(1 for b in result.blocks if b.truncated),
        }


# Singleton pour utilisation globale
_default_pruner: ContextPruner | None = None


def get_default_pruner() -> ContextPruner:
    """Retourne le pruner par défaut (singleton)."""
    global _default_pruner
    if _default_pruner is None:
        _default_pruner = ContextPruner()
    return _default_pruner
