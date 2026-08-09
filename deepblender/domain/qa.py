"""Objet domaine : QA (QAReport, Issue, RevisionSpec)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QAStatus(str, Enum):
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"


class IssueKind(str, Enum):
    TECHNICAL = "technical"
    VISUAL = "visual"
    CONTINUITY = "continuity"
    SEMANTIC = "semantic"


@dataclass
class Issue:
    """Un défaut relevé par le QA."""

    kind: IssueKind
    message: str
    step: str = ""


@dataclass
class QAReport:
    """Résultat typé du QA (Roadmap B §15)."""

    passed: bool
    score: float
    issues: list[Issue] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    @property
    def status(self) -> QAStatus:
        return QAStatus.PASS if self.passed else QAStatus.FAIL


@dataclass
class RevisionSpec:
    """Demande de révision ciblée vers l'étape concernée (jamais toute la production)."""

    issues: list[Issue]
    target_step: str
    instructions: str = ""
