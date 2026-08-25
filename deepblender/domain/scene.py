"""Specs structurées : SceneSpec, ShotSpec et sous-spécifications.

Le pipeline privilégie des specs typées (intention structurée) plutôt qu'un
brief transformé directement en script Python (Roadmap B §11).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RenderSpec:
    """Spécification explicite de rendu (résolution, fps, format, échantillons)."""

    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 24
    format: str = "mp4"
    samples: int = 64
    engine: str = "CYCLES"  # CYCLES | EEVEE

    def __post_init__(self):
        # Ensure resolution is a fixed-length tuple of 2 ints
        if isinstance(self.resolution, (list, tuple)) and len(self.resolution) == 2:
            self.resolution = (int(self.resolution[0]), int(self.resolution[1]))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "resolution": list(self.resolution),
            "fps": self.fps,
            "format": self.format,
            "samples": self.samples,
            "engine": self.engine,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RenderSpec":
        raw_resolution = data.get("resolution", (1920, 1080))
        return cls(
            resolution=(int(raw_resolution[0]), int(raw_resolution[1])),
            fps=data.get("fps", 24),
            format=data.get("format", "mp4"),
            samples=data.get("samples", 64),
            engine=data.get("engine", "CYCLES"),
        )


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
    """Personnage présent dans la scène.

    Un personnage peut parler plusieurs langues : ``main_language`` est sa
    langue principale, ``languages`` les langues secondaires éventuelles.
    """

    name: str
    description: str = ""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    main_language: str = ""
    languages: list[str] = field(default_factory=list)

    def spoken_languages(self) -> list[str]:
        """Langues parlées (principale en premier), sans doublon ni vide."""
        seen: list[str] = []
        for lang in [self.main_language, *self.languages]:
            if lang and lang not in seen:
                seen.append(lang)
        return seen

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "position": list(self.position),
            "main_language": self.main_language,
            "languages": list(self.languages),
        }


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
    render: RenderSpec = field(default_factory=RenderSpec)

    SCENE_SPEC_VERSION: int = 1

    def to_mapping(self) -> dict[str, Any]:
        """Sérialisation résumée pour le contexte agent (inchangée)."""
        return {
            "brief": self.brief,
            "environment": self.environment.description,
            "characters": [c.name for c in self.characters],
            "shots": len(self.shots),
        }

    def to_full_dict(self) -> dict[str, Any]:
        """Sérialisation complète pour persistance/versioning/patches.

        Récursive et JSON-safe : les sous-dataclasses (caméra, personnages…)
        sont aplaties via ``dataclasses.asdict``.
        """
        return {
            "schema_version": self.SCENE_SPEC_VERSION,
            "brief": self.brief,
            "environment": asdict(self.environment),
            "characters": [asdict(c) for c in self.characters],
            "shots": [asdict(s) for s in self.shots],
            "render": self.render.to_mapping(),
        }

    @classmethod
    def _character_from_dict(cls, data: dict[str, Any]) -> "CharacterSpec":
        payload = dict(data)
        position = payload.get("position")
        if isinstance(position, list):
            payload["position"] = (
                float(position[0]),
                float(position[1]),
                float(position[2]),
            )
        return CharacterSpec(**payload)

    @classmethod
    def _shot_from_dict(cls, data: dict[str, Any]) -> "ShotSpec":
        camera_data = data.get("camera") or {}
        camera = (
            CameraSpec(
                focal_length_mm=camera_data.get("focal_length_mm", 50.0),
                position=(
                    float(camera_data.get("position", (0.0, -5.0, 1.5))[0]),
                    float(camera_data.get("position", (0.0, -5.0, 1.5))[1]),
                    float(camera_data.get("position", (0.0, -5.0, 1.5))[2]),
                ),
                rotation=(
                    float(camera_data.get("rotation", (0.0, 0.0, 0.0))[0]),
                    float(camera_data.get("rotation", (0.0, 0.0, 0.0))[1]),
                    float(camera_data.get("rotation", (0.0, 0.0, 0.0))[2]),
                ),
            )
            if isinstance(camera_data, dict)
            else camera_data
        )
        env = EnvironmentSpec(**(data.get("environment") or {}))
        characters = [
            cls._character_from_dict(c) for c in (data.get("characters") or [])
        ]
        animation = AnimationSpec(**(data.get("animation") or {}))
        light_data = data.get("lighting") or {}
        raw_color = light_data.get("color", (1.0, 1.0, 1.0))
        lighting = LightingSpec(
            key_light=light_data.get("key_light", "area"),
            intensity=light_data.get("intensity", 1.0),
            color=(float(raw_color[0]), float(raw_color[1]), float(raw_color[2])),
        )
        return ShotSpec(
            duration=data.get("duration", 5.0),
            fps=data.get("fps", 24),
            camera=camera,
            environment=env,
            characters=characters,
            animation=animation,
            lighting=lighting,
        )

    @classmethod
    def from_full_dict(cls, data: dict[str, Any]) -> "SceneSpec":
        """Reconstruction depuis la sérialisation complète."""
        env_data = data.get("environment", {})
        env = EnvironmentSpec(**env_data)
        chars = [cls._character_from_dict(c) for c in data.get("characters", [])]
        shots = [cls._shot_from_dict(s) for s in data.get("shots", [])]
        render = RenderSpec.from_mapping(data.get("render", {}))
        return cls(
            brief=data.get("brief", ""),
            environment=env,
            characters=chars,
            shots=shots,
            render=render,
        )


@dataclass
class BlenderScript:
    """Script Blender (bpy) généré, prêt à être validé puis exécuté."""

    code: str
    scene_name: str
    version: int = 1


@dataclass
class RenderOutput:
    """Résultat du rendu : fichier vidéo/image produit par Blender."""

    video_path: str
    scene_name: str
    duration: float = 0.0
    fps: int = 24
    resolution: tuple[int, int] = (1920, 1080)
    format: str = "mp4"
    version: int = 1

    def to_mapping(self) -> dict[str, Any]:
        return {
            "video_path": self.video_path,
            "scene_name": self.scene_name,
            "duration": self.duration,
            "fps": self.fps,
            "resolution": list(self.resolution),
            "format": self.format,
            "version": self.version,
        }


@dataclass
class FinalOutput:
    """Sortie finale : vidéo + audio + sous-titres fusionnés."""

    output_path: str
    scene_name: str
    duration: float = 0.0
    fps: int = 24
    resolution: tuple[int, int] = (1920, 1080)
    format: str = "mp4"
    version: int = 1
    has_audio: bool = False
    has_subtitles: bool = False

    def to_mapping(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "scene_name": self.scene_name,
            "duration": self.duration,
            "fps": self.fps,
            "resolution": list(self.resolution),
            "format": self.format,
            "version": self.version,
            "has_audio": self.has_audio,
            "has_subtitles": self.has_subtitles,
        }
