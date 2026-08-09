"""Specs structurées : SceneSpec, ShotSpec et sous-spécifications.

Le pipeline privilégie des specs typées (intention structurée) plutôt qu'un
brief transformé directement en script Python (Roadmap B §11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CameraSpec:
    """Spécification de caméra pour un plan."""

    focal_length_mm: float = 50.0
    position: tuple[float, float, float] = (0.0, -5.0, 1.5)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class EnvironmentSpec:
    """Ambiance du plan : décor et conditions."""

    description: str = ""
    lighting_mood: str = "neutral"
    rain: bool = False


@dataclass
class CharacterSpec:
    """Personnage présent dans la scène."""

    name: str
    description: str = ""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class AnimationSpec:
    """Mouvement demandé (personnage / objet / caméra)."""

    description: str = ""


@dataclass
class LightingSpec:
    """Configuration d'éclairage."""

    key_light: str = "area"
    intensity: float = 1.0
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class ShotSpec:
    """Spec d'un plan : caméra, décor, personnages, animation, lumière."""

    duration: float = 5.0
    fps: int = 24
    camera: CameraSpec = field(default_factory=CameraSpec)
    environment: EnvironmentSpec = field(default_factory=EnvironmentSpec)
    characters: list[CharacterSpec] = field(default_factory=list)
    animation: AnimationSpec = field(default_factory=AnimationSpec)
    lighting: LightingSpec = field(default_factory=LightingSpec)

    def frame_count(self) -> int:
        """Nombre de frames du plan (logique déterministe, P3)."""
        return round(self.duration * self.fps)


@dataclass
class SceneSpec:
    """Spec complète d'une scène, produite par le DirectorAgent."""

    brief: str
    environment: EnvironmentSpec = field(default_factory=EnvironmentSpec)
    characters: list[CharacterSpec] = field(default_factory=list)
    shots: list[ShotSpec] = field(default_factory=list)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "brief": self.brief,
            "environment": self.environment.description,
            "characters": [c.name for c in self.characters],
            "shots": len(self.shots),
        }


@dataclass
class BlenderScript:
    """Script Blender (bpy) généré, prêt à être validé puis exécuté."""

    code: str
    scene_name: str
    version: int = 1
