"""Specs structurées : SceneSpec, ShotSpec et sous-spécifications.

Le pipeline privilégie des specs typées (intention structurée) plutôt qu'un
brief transformé directement en script Python (Roadmap B §11).
"""

from __future__ import annotations

import dataclasses
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


# ── helpers de coercition ────────────────────────────────────────────────
# Les agents produisent parfois des dicts/listes là où la spec attend une
# dataclass (ex: ``animation={"description": ...}`` au lieu d'une AnimationSpec).
# Toutes les specs ci-dessous appliquent une __post_init__ défensive pour que
# les étapes en aval (blender, env, character...) voient toujours des dataclasses.


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "oui", "on")
    return bool(value)


def _as_tuple3(value: Any, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except (TypeError, ValueError):
            return default
    return default


def _as_tuple2(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return (int(value[0]), int(value[1]))
        except (TypeError, ValueError):
            return default
    return default


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v for v in (v.strip() for v in value.split(",")) if v]
    if isinstance(value, (list, tuple)):
        return [_as_str(v) for v in value if _as_str(v)]
    return []


def _default_instance(cls: type):
    """Instance par défaut de ``cls``, en fournissant les champs requis.

    ``CharacterSpec`` exige ``name`` (pas de valeur par défaut) : plutôt que
    de laisser ``cls()`` lever un ``TypeError`` qui casserait la pipeline, on
    inspecte les champs du dataclass et on comble les champs sans défaut.
    """
    try:
        return cls()
    except TypeError:
        pass
    fields = getattr(cls, "__dataclass_fields__", {})
    kwargs = {}
    for fname, f in fields.items():
        if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING:
            continue
        if fname == "name":
            kwargs[fname] = ""
        else:
            kwargs[fname] = None
    return cls(**kwargs) if kwargs else cls()


def _coerce_or_instance(cls: type, value: Any):
    """Renvoie une instance de ``cls``, en coercant dict/str/None.

    Les agents produisent des valeurs hétérogènes : dict (``{...}``),
    chaîne (un nom de personnage seul), ``None`` ou un objet du bon type.
    ``name`` n'a pas de valeur par défaut (``CharacterSpec``) donc ``cls()``
    seul peut échouer : on essaie ``cls(name=...)`` pour une chaîne, puis une
    instance par défaut robuste — sans jamais lever de ``TypeError`` qui
    casserait la pipeline.
    """
    if isinstance(value, cls):
        return value
    if value is None:
        return _default_instance(cls)
    if isinstance(value, dict):
        try:
            return cls(**{k: v for k, v in value.items()})
        except TypeError:
            return _default_instance(cls)
    if isinstance(value, str):
        try:
            return cls(name=value)
        except TypeError:
            return _default_instance(cls)
    return _default_instance(cls)


# Moteurs de rendu supportés
ENGINE_BLENDER = "BLENDER"
SUPPORTED_ENGINES = (ENGINE_BLENDER,)


@dataclass
class RenderSpec:
    """Paramètres de rendu : résolution, fps, format, moteur.

    Le champ ``engine`` détermine l'agent et le bridge utilisés :
    - CYCLES/EEVEE/BLENDER : BlenderAgent → BlenderBridge
    """

    resolution: tuple[int, int] = (1920, 1080)  # largeur x hauteur en pixels
    fps: int = 24  # images par seconde
    format: str = "mp4"  # format de sortie : mp4, png, exr
    samples: int = 256  # échantillons par pixel (qualité du débruitage)
    engine: str = "CYCLES"  # moteur : CYCLES | EEVEE | BLENDER
    denoise: bool = True  # active le débruitage OIDN (réduit le bruit)
    use_gpu: bool = True  # utilise le GPU CUDA/OptiX si disponible
    output_format: str = "OPEN_EXR_MULTILAYER"  # format de sortie Blender (exr, png, mp4)

    def __post_init__(self):
        self.resolution = _as_tuple2(self.resolution, (1920, 1080))
        self.fps = _as_int(self.fps, 24)
        self.format = _as_str(self.format, "mp4")
        self.samples = _as_int(self.samples, 256)
        self.engine = _as_str(self.engine, "CYCLES")
        self.denoise = _as_bool(self.denoise)
        self.use_gpu = _as_bool(self.use_gpu)
        self.output_format = _as_str(self.output_format, "OPEN_EXR_MULTILAYER")

    def is_blender_engine(self) -> bool:
        """True si le moteur est un variant de Blender."""
        return self.engine.upper() in ("CYCLES", "EEVEE", "BLENDER", "")

    def to_mapping(self) -> dict[str, Any]:
        result = {
            "resolution": list(self.resolution),
            "fps": self.fps,
            "format": self.format,
            "samples": self.samples,
            "engine": self.engine,
            "denoise": self.denoise,
            "use_gpu": self.use_gpu,
            "output_format": self.output_format,
        }
        return result

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RenderSpec":
        raw_resolution = data.get("resolution", (1920, 1080))
        return cls(
            resolution=(int(raw_resolution[0]), int(raw_resolution[1])),
            fps=data.get("fps", 24),
            format=data.get("format", "mp4"),
            samples=data.get("samples", 256),
            engine=data.get("engine", "CYCLES"),
            denoise=data.get("denoise", True),
            use_gpu=data.get("use_gpu", True),
            output_format=data.get("output_format", "OPEN_EXR_MULTILAYER"),
        )


@dataclass
class CameraSpec:
    """Configuration de caméra pour un plan : focale, position, rotation.

    La position et rotation sont en coordonnées Blender (unités métriques).
    """

    focal_length_mm: float = 50.0  # longueur focale en millimètres
    position: tuple[float, float, float] = (0.0, -5.0, 1.5)  # (x, y, z) en mètres
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)  # (roll, pitch, yaw) en degrés

    def __post_init__(self) -> None:
        self.focal_length_mm = _as_float(self.focal_length_mm, 50.0)
        self.position = _as_tuple3(self.position, (0.0, -5.0, 1.5))
        self.rotation = _as_tuple3(self.rotation, (0.0, 0.0, 0.0))


@dataclass
class EnvironmentSpec:
    """Ambiance du plan : décor, éclairage et conditions atmosphériques.

    Décrit l'environnement dans lequel se déroule le plan.
    """

    description: str = ""  # description textuelle du décor (ex: "forêt sombre et brumeuse")
    lighting_mood: str = "neutral"  # ambiance lumineuse : neutral, warm, cold, dramatic, cinematic
    rain: bool = False  # active la pluie et les flaques

    def __post_init__(self) -> None:
        self.description = _as_str(self.description)
        self.lighting_mood = _as_str(self.lighting_mood, "neutral")
        self.rain = _as_bool(self.rain)


@dataclass
class CharacterSpec:
    """Personnage présent dans la scène : nom, apparence, position, langues.

    Un personnage peut parler plusieurs langues : ``main_language`` est sa
    langue principale, ``languages`` les langues secondaires éventuelles.
    """

    name: str  # nom du personnage (identifiant unique dans la scène)
    description: str = ""  # description visuelle et comportementale
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)  # (x, y, z) position initiale
    main_language: str = ""  # langue principale parlée (code ISO : fr, en, wo, ar...)
    languages: list[str] = field(default_factory=list)  # langues secondaires
    asset_id: str = ""  # identifiant de l'asset 3D (ex: "quaternius__animated_woman")
    asset_source: str = ""  # source : "quaternius", "mixamo", "polyhaven", "fallback", ""

    def __post_init__(self) -> None:
        self.name = _as_str(self.name)
        self.description = _as_str(self.description)
        self.position = _as_tuple3(self.position, (0.0, 0.0, 0.0))
        self.main_language = _as_str(self.main_language)
        self.languages = _as_str_list(self.languages)
        if not self.main_language and self.languages:
            self.main_language = self.languages[0]
        self.asset_id = _as_str(self.asset_id)
        self.asset_source = _as_str(self.asset_source)

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
            "asset_id": self.asset_id,
            "asset_source": self.asset_source,
        }


@dataclass
class AnimationSpec:
    """Mouvement demandé pour un personnage, objet ou caméra dans un plan.

    Décrit l'action à animer en langage naturel.
    """

    description: str = ""  # ex: "le personnage lève le bras et attrape la tasse"

    def __post_init__(self) -> None:
        self.description = _as_str(self.description)


@dataclass
class LightingSpec:
    """Configuration d'éclairage pour un plan : source, intensité, couleur.

    Utilisé par EnvironmentArtistAgent pour placer les lights dans la scène 3D.
    """

    key_light: str = "area"  # type de lumière principale : area, point, sun, spot
    intensity: float = 1.0  # intensité relative (0.0 à 2.0)
    color: tuple[float, float, float] = (1.0, 1.0, 1.0) # couleur RGB normalisée (0-1)

    def __post_init__(self) -> None:
        self.key_light = _as_str(self.key_light, "area")
        self.intensity = _as_float(self.intensity, 1.0)
        self.color = _as_tuple3(self.color, (1.0, 1.0, 1.0))


@dataclass
class ShotSpec:
    """Spec d'un plan : caméra, décor, personnages, animation, lumière.

    Représente un plan individuel du storyboard. Chaque plan a sa propre
    configuration de caméra, environnement, personnages et animation.
    """

    duration: float = 5.0  # durée en secondes
    fps: int = 24  # images par seconde pour ce plan
    camera: CameraSpec = field(default_factory=CameraSpec)  # configuration caméra
    environment: EnvironmentSpec = field(default_factory=EnvironmentSpec)  # décor
    characters: list[CharacterSpec] = field(default_factory=list)  # personnages présents
    animation: AnimationSpec = field(default_factory=AnimationSpec)  # mouvement
    lighting: LightingSpec = field(default_factory=LightingSpec)  # éclairage

    def __post_init__(self) -> None:
        """Coerce les dicts produits par l'agent en sous-dataclasses.

        Sans cela, un ``ShotSpec(animation={"description": ...})`` laissait un
        ``dict`` dans le champ ``animation`` et l'étape suivante explosait sur
        ``shot.animation.description`` (AttributError).
        """
        self.duration = _as_float(self.duration, 5.0)
        self.fps = _as_int(self.fps, 24)
        self.camera = _coerce_or_instance(CameraSpec, self.camera)
        self.environment = _coerce_or_instance(EnvironmentSpec, self.environment)
        if isinstance(self.characters, (list, tuple)):
            self.characters = [
                _coerce_or_instance(CharacterSpec, c) for c in self.characters
            ]
        else:
            self.characters = []
        self.animation = _coerce_or_instance(AnimationSpec, self.animation)
        self.lighting = _coerce_or_instance(LightingSpec, self.lighting)

    def frame_count(self) -> int:
        """Nombre de frames du plan (logique déterministe, P3)."""
        return round(self.duration * self.fps)


@dataclass
class SceneSpec:
    """Spec complète d'une scène : brief, environnement, personnages, plans.

    Produite par le DirectorAgent à partir du brief. Chaque agent du pipeline
    lit cette spec pour produire son output (storyboard, script, rendu, audio...).
    """

    brief: str  # brief initial de l'utilisateur
    environment: EnvironmentSpec = field(default_factory=EnvironmentSpec)  # décor global
    characters: list[CharacterSpec] = field(default_factory=list)  # tous les personnages
    shots: list[ShotSpec] = field(default_factory=list)  # liste ordonnée des plans
    render: RenderSpec = field(default_factory=RenderSpec)  # paramètres de rendu

    SCENE_SPEC_VERSION: int = 1

    def __post_init__(self) -> None:
        """Coerce les dicts produits par l'agent aux niveaux supérieurs."""
        self.brief = _as_str(self.brief)
        self.environment = _coerce_or_instance(EnvironmentSpec, self.environment)
        if isinstance(self.characters, (list, tuple)):
            self.characters = [
                _coerce_or_instance(CharacterSpec, c) for c in self.characters
            ]
        else:
            self.characters = []
        if isinstance(self.shots, (list, tuple)):
            self.shots = [_coerce_or_instance(ShotSpec, s) for s in self.shots]
        else:
            self.shots = []
        if isinstance(self.render, dict):
            self.render = (
                RenderSpec.from_mapping(self.render)
                if "fps" in self.render
                else RenderSpec(**(self.render or {}))
            )
        else:
            self.render = _coerce_or_instance(RenderSpec, self.render)

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
        sont aplaties via ``dataclasses.asdict``. Défensif : un champ produit
        par l'agent peut être ``None`` ou déjà un ``dict`` (rare mais observé
        en production) — on ne fait pas exploser la sérialisation pour ça.
        """

        def _asdict(value: Any) -> Any:
            if is_dataclass(value):
                return asdict(value)
            if isinstance(value, dict):
                return {k: _asdict(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [_asdict(v) for v in value]
            return value

        render = self.render
        render_mapping = (
            render.to_mapping() if is_dataclass(render) else _asdict(render)
        )
        return {
            "schema_version": self.SCENE_SPEC_VERSION,
            "brief": self.brief,
            "environment": _asdict(self.environment),
            "characters": [_asdict(c) for c in self.characters],
            "shots": [_asdict(s) for s in self.shots],
            "render": render_mapping,
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
        # Handle new asset fields
        payload.setdefault("asset_id", "")
        payload.setdefault("asset_source", "")
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
    """Script Blender (bpy) généré par BlenderAgent, prêt à être validé puis exécuté.

    Contient le code Python complet qui crée la scène 3D dans Blender.
    """

    code: str  # code Python Blender complet (bpy)
    scene_name: str  # nom de la scène Blender
    version: int = 1  # numéro de version du script


@dataclass
class RenderOutput:
    """Résultat du rendu : fichier vidéo/image produit par Blender.

    Généré après exécution du BlenderScript dans Blender.
    """

    video_path: str  # chemin vers le fichier vidéo de sortie
    scene_name: str  # nom de la scène rendue
    duration: float = 0.0  # durée en secondes
    fps: int = 24  # images par seconde
    resolution: tuple[int, int] = (1920, 1080)  # résolution en pixels
    format: str = "mp4"  # format du fichier
    version: int = 1  # numéro de version du rendu

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
    """Sortie finale : vidéo + audio + sous-titres fusionnés.

    Résultat final du pipeline après compositing et merge.
    """

    output_path: str  # chemin vers le fichier final
    scene_name: str  # nom de la scène
    duration: float = 0.0  # durée en secondes
    fps: int = 24  # images par seconde
    resolution: tuple[int, int] = (1920, 1080)  # résolution en pixels
    format: str = "mp4" # format de sortie
    version: int = 1  # numéro de version
    has_audio: bool = False  # contient une piste audio mixée
    has_subtitles: bool = False  # contient des sous-titres brûlés

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
