"""Objet domaine : Project, Sequence, Shot, Brief."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import uuid4

from deepblender.domain.scene import SceneSpec


def _new_id() -> str:
    return uuid4().hex[:8]


@dataclass
class Brief:
    """Intention créative de départ, non structurée."""

    text: str
    id: str = field(default_factory=_new_id)
    created_at: float = field(default_factory=time.time)

    def __str__(self) -> str:
        return self.text


@dataclass
class Shot:
    """Un plan de la production, lié à sa spec et à ses artifacts."""

    name: str
    spec: SceneSpec | None = None
    id: str = field(default_factory=_new_id)
    status: str = "planned"


@dataclass
class Sequence:
    """Une séquence regroupant des plans."""

    name: str
    shots: dict[str, Shot] = field(default_factory=dict)
    id: str = field(default_factory=_new_id)

    def add_shot(self, shot: Shot) -> None:
        self.shots[shot.name] = shot


@dataclass
class Project:
    """Vérité persistante d'une production : contraintes globales + séquences."""

    name: str
    brief: Brief
    sequences: dict[str, Sequence] = field(default_factory=dict)
    id: str = field(default_factory=_new_id)

    def add_sequence(self, sequence: Sequence) -> None:
        self.sequences[sequence.name] = sequence

    def all_shots(self) -> list[Shot]:
        return [shot for seq in self.sequences.values() for shot in seq.shots.values()]
