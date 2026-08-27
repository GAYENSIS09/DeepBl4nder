"""Objet domaine : QA (QAReport, Issue, RevisionSpec).

Structures pour le contrôle qualité et les demandes de révision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QAStatus(str, Enum):
    """Statut du contrôle qualité."""
    PENDING = "pending"  # en attente d'évaluation
    PASS = "pass"  # validation OK
    FAIL = "fail"  # échec, révision nécessaire


class IssueKind(str, Enum):
    """Type de défaut relevé par le QA."""
    TECHNICAL = "technical"  # erreur technique (script, syntaxe, crash)
    VISUAL = "visual"  # problème visuel (rendu, texture, animation)
    CONTINUITY = "continuity"  # incohérence narrative ou visuelle
    SEMANTIC = "semantic"  # problème de sens ou d'interprétation


@dataclass
class Issue:
    """Un défaut relevé par le QA : type, message, étape concernée.

    Chaque issue cible une étape spécifique du pipeline pour permettre
    une révision précise (pas de révision sur toute la production).
    """

    kind: IssueKind  # type de défaut
    message: str  # description du problème
    step: str = ""  # étape ciblée : director, blender, qa, animation...

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            self.kind = IssueKind(self.kind)


@dataclass
class QAReport:
    """Résultat du contrôle qualité : verdict, score, issues, recommandations.

    Produit par QAAgent. Le verdict (passed/failed) détermine si le pipeline
    continue ou déclenche une révision. Le score (0-100) mesure la qualité.
    """

    passed: bool  # True si le rendu est acceptable
    score: float  # score de qualité (0.0 à 100.0)
    issues: list[Issue] = field(default_factory=list)  # liste des défauts trouvés
    recommendations: list[str] = field(default_factory=list)  # suggestions d'amélioration

    @property
    def status(self) -> QAStatus:
        return QAStatus.PASS if self.passed else QAStatus.FAIL


@dataclass
class RevisionSpec:
    """Demande de révision ciblée vers l'étape concernée.

    Contient les issues à corriger et les instructions pour l'agent cible.
    Ne jamais appliquer de révision sur toute la production.
    """

    issues: list[Issue]  # issues à corriger
    target_step: str  # étape ciblée : director, blender, animation...
    instructions: str = ""  # instructions détaillées pour la correction
