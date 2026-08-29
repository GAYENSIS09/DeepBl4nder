"""Specs structurées : SceneSpec, ShotSpec et sous-spécifications.

Le pipeline privilégie des specs typées (intention structurée) plutôt qu'un
brief transformé directement en script Python (Roadmap B §11).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# Moteurs de rendu supportés
ENGINE_BLENDER = "BLENDER"
ENGINE_UE5 = "UE5"
ENGINE_GODOT = "GODOT"
ENGINE_AI_VIDEO = "AI_VIDEO"
SUPPORTED_ENGINES = (ENGINE_BLENDER, ENGINE_UE5, ENGINE_GODOT, ENGINE_AI_VIDEO)


@dataclass
class UE5RenderSpec:
    """Paramètres spécifiques à Unreal Engine 5.

    Utilisé par UE5Agent pour configurer le rendu Lumen/Nanite/MRQ.
    """

    use_lumen: bool = True  # Global illumination Lumen (réaliste)
    use_nanite: bool = True  # Géométrie virtualisée (performant)
    use_ray_tracing: bool = False  # Ray tracing hardware (lent mais fidèle)
    quality_preset: str = "cinematic"  # epic | cinematic
    console_variables: dict[str, float] = field(default_factory=dict)  # CV custom

    def to_mapping(self) -> dict[str, Any]:
        return {
            "use_lumen": self.use_lumen,
            "use_nanite": self.use_nanite,
            "use_ray_tracing": self.use_ray_tracing,
            "quality_preset": self.quality_preset,
            "console_variables": dict(self.console_variables),
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "UE5RenderSpec":
        return cls(
            use_lumen=data.get("use_lumen", True),
            use_nanite=data.get("use_nanite", True),
            use_ray_tracing=data.get("use_ray_tracing", False),
            quality_preset=data.get("quality_preset", "cinematic"),
            console_variables=data.get("console_variables", {}),
        )


@dataclass
class GodotRenderSpec:
    """Paramètres spécifiques à Godot 4.

    Utilisé par GodotAgent pour configurer le rendu PBR/WebGL.
    """

    use_glow: bool = True  # Effet bloom/glow
    ambient_light_energy: float = 0.3  # Intensité de la lumière ambiante
    export_webgl: bool = False  # Exporter en WebGL pour le web
    msaa: int = 2  # Anti-aliasing (0, 2, 4, 8)
    fov: float = 75.0  # Champ de vision de la caméra

    def to_mapping(self) -> dict[str, Any]:
        return {
            "use_glow": self.use_glow,
            "ambient_light_energy": self.ambient_light_energy,
            "export_webgl": self.export_webgl,
            "msaa": self.msaa,
            "fov": self.fov,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "GodotRenderSpec":
        return cls(
            use_glow=data.get("use_glow", True),
            ambient_light_energy=data.get("ambient_light_energy", 0.3),
            export_webgl=data.get("export_webgl", False),
            msaa=data.get("msaa", 2),
            fov=data.get("fov", 75.0),
        )


@dataclass
class AIVideoRenderSpec:
    """Paramètres spécifiques à la génération vidéo par IA.

    Utilisé par AIVideoAgent pour configurer les modèles de diffusion.
    """

    model: str = "cogvideox"  # cogvideox, wan2.1, animatediff, svd
    mode: str = "t2v"  # t2v (text-to-video), i2v (image-to-video)
    seed: int = 42  # Seed pour la reproductibilité
    num_frames: int = 49  # Nombre de frames (4-8 secondes)
    guidance_scale: float = 6.0  # Force du prompt
    num_inference_steps: int = 50  # Étapes d'inférence
    motion_bucket_id: int = 127  # Intensité du mouvement (SVD)
    use_cache: bool = True  # Activer le cache des générations

    def to_mapping(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "mode": self.mode,
            "seed": self.seed,
            "num_frames": self.num_frames,
            "guidance_scale": self.guidance_scale,
            "num_inference_steps": self.num_inference_steps,
            "motion_bucket_id": self.motion_bucket_id,
            "use_cache": self.use_cache,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AIVideoRenderSpec":
        return cls(
            model=data.get("model", "cogvideox"),
            mode=data.get("mode", "t2v"),
            seed=data.get("seed", 42),
            num_frames=data.get("num_frames", 49),
            guidance_scale=data.get("guidance_scale", 6.0),
            num_inference_steps=data.get("num_inference_steps", 50),
            motion_bucket_id=data.get("motion_bucket_id", 127),
            use_cache=data.get("use_cache", True),
        )


@dataclass
class RenderSpec:
    """Paramètres de rendu : résolution, fps, format, moteur.

    Le champ ``engine`` détermine quel agent et bridge sont utilisés :
    - BLENDER/CYCLES/EEVEE : BlenderAgent → BlenderBridge
    - UE5 : UE5Agent → UE5Bridge (REST API)
    - GODOT : GodotAgent → GodotBridge (CLI)
    - AI_VIDEO : AIVideoAgent → DiffusionBridge (GPU)
    """

    resolution: tuple[int, int] = (1920, 1080)  # largeur x hauteur en pixels
    fps: int = 24  # images par seconde
    format: str = "mp4"  # format de sortie : mp4, png, exr
    samples: int = 256  # échantillons par pixel (qualité du débruitage)
    engine: str = "CYCLES"  # moteur : CYCLES | EEVEE | BLENDER | UE5 | GODOT | AI_VIDEO
    denoise: bool = True  # active le débruitage OIDN (réduit le bruit)
    use_gpu: bool = True  # utilise le GPU CUDA/OptiX si disponible
    output_format: str = "OPEN_EXR_MULTILAYER"  # format de sortie Blender (exr, png, mp4)
    ue5: UE5RenderSpec | None = None  # settings spécifiques UE5 (si engine=UE5)
    godot: GodotRenderSpec | None = None  # settings spécifiques Godot (si engine=GODOT)
    ai_video: AIVideoRenderSpec | None = None  # settings spécifiques AI Video (si engine=AI_VIDEO)

    def __post_init__(self):
        # Ensure resolution is a fixed-length tuple of 2 ints
        if isinstance(self.resolution, (list, tuple)) and len(self.resolution) == 2:
            self.resolution = (int(self.resolution[0]), int(self.resolution[1]))

    def is_blender_engine(self) -> bool:
        """True si le moteur est un variant de Blender."""
        return self.engine.upper() in ("CYCLES", "EEVEE", "BLENDER", "")

    def is_ue5_engine(self) -> bool:
        """True si le moteur est Unreal Engine 5."""
        return self.engine.upper() == "UE5"

    def is_godot_engine(self) -> bool:
        """True si le moteur est Godot 4."""
        return self.engine.upper() == "GODOT"

    def is_ai_video_engine(self) -> bool:
        """True si le moteur est un moteur AI Video."""
        return self.engine.upper() == "AI_VIDEO"

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
        if self.ue5 is not None:
            result["ue5"] = self.ue5.to_mapping()
        if self.godot is not None:
            result["godot"] = self.godot.to_mapping()
        if self.ai_video is not None:
            result["ai_video"] = self.ai_video.to_mapping()
        return result

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RenderSpec":
        raw_resolution = data.get("resolution", (1920, 1080))
        ue5_data = data.get("ue5")
        ue5 = UE5RenderSpec.from_mapping(ue5_data) if ue5_data else None
        godot_data = data.get("godot")
        godot = GodotRenderSpec.from_mapping(godot_data) if godot_data else None
        ai_video_data = data.get("ai_video")
        ai_video = AIVideoRenderSpec.from_mapping(ai_video_data) if ai_video_data else None
        return cls(
            resolution=(int(raw_resolution[0]), int(raw_resolution[1])),
            fps=data.get("fps", 24),
            format=data.get("format", "mp4"),
            samples=data.get("samples", 256),
            engine=data.get("engine", "CYCLES"),
            denoise=data.get("denoise", True),
            use_gpu=data.get("use_gpu", True),
            output_format=data.get("output_format", "OPEN_EXR_MULTILAYER"),
            ue5=ue5,
            godot=godot,
            ai_video=ai_video,
        )


@dataclass
class CameraSpec:
    """Configuration de caméra pour un plan : focale, position, rotation.

    La position et rotation sont en coordonnées Blender (unités métriques).
    """

    focal_length_mm: float = 50.0  # longueur focale en millimètres
    position: tuple[float, float, float] = (0.0, -5.0, 1.5)  # (x, y, z) en mètres
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)  # (roll, pitch, yaw) en degrés


@dataclass
class EnvironmentSpec:
    """Ambiance du plan : décor, éclairage et conditions atmosphériques.

    Décrit l'environnement dans lequel se déroule le plan.
    """

    description: str = ""  # description textuelle du décor (ex: "forêt sombre et brumeuse")
    lighting_mood: str = "neutral"  # ambiance lumineuse : neutral, warm, cold, dramatic, cinematic
    rain: bool = False  # active la pluie et les flaques


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


@dataclass
class LightingSpec:
    """Configuration d'éclairage pour un plan : source, intensité, couleur.

    Utilisé par EnvironmentArtistAgent pour placer les lights dans la scène 3D.
    """

    key_light: str = "area"  # type de lumière principale : area, point, sun, spot
    intensity: float = 1.0  # intensité relative (0.0 à 2.0)
    color: tuple[float, float, float] = (1.0, 1.0, 1.0) # couleur RGB normalisée (0-1)


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
