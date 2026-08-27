"""Specs structurées du pipeline média : audio, compositing et langues.

Couvre les étapes 14-18 du pipeline audiovisuel : compositing,
audio (sound design, musique, voix) et localisation (dialogues, sous-titres,
métadonnées, interface).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class CharacterModel:
    """Modèle 3D d'un personnage : géométrie, matériaux, squelette, blendshapes.

    Utilisé par CharacterDesignerAgent pour définir la structure du modèle
    et par BlenderAgent pour l'instancier dans la scène.
    """

    def __init__(
        self,
        name: str,  # nom unique du personnage
        description: str,  # description visuelle et comportementale
        geometry_type: str = "primitive",  # type de géométrie : primitive, mesh, curve, text
        material: str | None = None,  # nom du matériau PBR
        skeleton_type: str | None = None,  # type de squelette : humanoid, quadruped, custom
        blendshapes: list[str] | None = None,  # morph targets pour l'animation faciale
        scale: tuple[float, float, float] = (1.0, 1.0, 1.0),  # échelle (x, y, z)
        import_path: str | None = None,  # chemin vers un modèle existant (.glb, .fbx)
    ) -> None:
        self.name = name
        self.description = description
        self.geometry_type = geometry_type
        self.material = material
        self.skeleton_type = skeleton_type
        self.blendshapes = blendshapes or []
        self.scale = scale
        self.import_path = import_path

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "geometry_type": self.geometry_type,
            "material": self.material,
            "skeleton_type": self.skeleton_type,
            "blendshapes": self.blendshapes,
            "scale": list(self.scale),
            "import_path": self.import_path,
        }


class CharacterDesignResult:
    """Résultat de la conception de personnages : liste de modèles, style, échelle.

    Produit par CharacterDesignerAgent. Contient les specifications de tous
    les personnages de la scène pour le reste du pipeline.
    """

    def __init__(
        self,
        characters: list[CharacterModel],  # modèles de personnages créés
        style: str = "realistic",  # style visuel : realistic, cartoon, anime, lowpoly
        scale: float = 1.0,  # échelle globale des personnages
    ) -> None:
        self.characters = characters
        self.style = style
        self.scale = scale

    def to_mapping(self) -> dict[str, Any]:
        return {
            "characters": [c.to_mapping() for c in self.characters],
            "style": self.style,
            "scale": self.scale,
        }


class EnvironmentAsset:
    """Un asset 3D pour l'environnement : type, matériau, texture, position.

    Représente un élément du décor (sol, bâtiment, arbre, meuble...).
    Les assets CC0 de PolyHaven sont privilégiés quand disponibles.
    """

    def __init__(
        self,
        name: str,  # nom de l'asset
        asset_type: str = "primitive",  # type : primitive, mesh, collection, hdri
        description: str = "",  # description de l'asset
        material: str | None = None,  # matériau PBR appliqué
        texture_source: str | None = None,  # source de la texture (PolyHaven, procedural)
        hdri_source: str | None = None,  # source HDRI pour l'éclairage
        position: tuple[float, float, float] = (0.0, 0.0, 0.0),  # position (x, y, z)
        scale: tuple[float, float, float] = (1.0, 1.0, 1.0),  # échelle (x, y, z)
        import_path: str | None = None,  # chemin vers un asset existant
        cc0: bool = True,  # licence CC0 (domaine public)
    ) -> None:
        self.name = name
        self.asset_type = asset_type
        self.description = description
        self.material = material
        self.texture_source = texture_source
        self.hdri_source = hdri_source
        self.position = position
        self.scale = scale
        self.import_path = import_path
        self.cc0 = cc0

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "asset_type": self.asset_type,
            "description": self.description,
            "material": self.material,
            "texture_source": self.texture_source,
            "hdri_source": self.hdri_source,
            "position": list(self.position),
            "scale": list(self.scale),
            "import_path": self.import_path,
            "cc0": self.cc0,
        }


class LightingSetup:
    """Configuration d'éclairage : HDRI, lumières principales, bords, brouillard.

    Définit l'ambiance lumineuse complète de l'environnement 3D.
    """

    def __init__(
        self,
        hdri_name: str | None = None,  # nom de la map HDRI (PolyHaven)
        key_light_type: str = "AREA",  # type de lumière principale : AREA, POINT, SUN, SPOT
        key_light_energy: float = 400.0,  # intensité de la lumière principale (watts)
        key_light_position: tuple[float, float, float] = (5.0, -5.0, 8.0),  # position (x, y, z)
        fill_light_energy: float = 100.0,  # intensité de la lumière de remplissage
        rim_light_energy: float = 200.0,  # intensité de la lumière de contour
        ambient_color: tuple[float, float, float] = (0.05, 0.05, 0.06),  # couleur ambiante RGB
        fog_density: float = 0.0,  # densité du brouillard (0.0 = désactivé)
        fog_color: tuple[float, float, float] = (0.5, 0.5, 0.55),  # couleur du brouillard RGB
    ) -> None:
        self.hdri_name = hdri_name
        self.key_light_type = key_light_type
        self.key_light_energy = key_light_energy
        self.key_light_position = key_light_position
        self.fill_light_energy = fill_light_energy
        self.rim_light_energy = rim_light_energy
        self.ambient_color = ambient_color
        self.fog_density = fog_density
        self.fog_color = fog_color

    def to_mapping(self) -> dict[str, Any]:
        return {
            "hdri_name": self.hdri_name,
            "key_light_type": self.key_light_type,
            "key_light_energy": self.key_light_energy,
            "key_light_position": list(self.key_light_position),
            "fill_light_energy": self.fill_light_energy,
            "rim_light_energy": self.rim_light_energy,
            "ambient_color": list(self.ambient_color),
            "fog_density": self.fog_density,
            "fog_color": list(self.fog_color),
        }


class EnvironmentDesignResult:
    """Résultat de la conception d'environnement : assets, éclairage, sol, ciel.

    Produit par EnvironmentArtistAgent. Contient toutes les spécifications
    pour créer l'environnement 3D dans Blender.
    """

    def __init__(
        self,
        assets: list[EnvironmentAsset],  # liste des assets du décor
        lighting: LightingSetup | None = None,  # configuration d'éclairage
        ground_type: str = "plane",  # type de sol : plane, grid, displacement
        ground_size: float = 40.0,  # taille du sol en unités Blender
        sky_type: str = "world",  # type de ciel : world, hdri, procedural
        hdri_name: str | None = None,  # nom de la map HDRI globale
        fog_enabled: bool = False,  # brouillard atmosphérique activé
        particle_systems: list[dict[str, Any]] | None = None,  # systèmes de particules
    ) -> None:
        self.assets = assets
        self.lighting = lighting or LightingSetup()
        self.ground_type = ground_type
        self.ground_size = ground_size
        self.sky_type = sky_type
        self.hdri_name = hdri_name
        self.fog_enabled = fog_enabled
        self.particle_systems = particle_systems or []

    def to_mapping(self) -> dict[str, Any]:
        return {
            "assets": [a.to_mapping() for a in self.assets],
            "lighting": self.lighting.to_mapping(),
            "ground_type": self.ground_type,
            "ground_size": self.ground_size,
            "sky_type": self.sky_type,
            "hdri_name": self.hdri_name,
            "fog_enabled": self.fog_enabled,
            "particle_systems": self.particle_systems,
        }


class Keyframe:
    """Un keyframe d'animation : frame, propriété, valeur, interpolation.

    Représente un point clé dans le temps pour une propriété animée.
    """

    def __init__(
        self,
        frame: int,  # numéro de frame (0-based)
        property_path: str,  # chemin de la propriété (ex: "location", "rotation_euler")
        value: Any,  # valeur à cette frame (tuple pour location/rotation)
        interpolation: str = "BEZIER",  # type d'interpolation : BEZIER, LINEAR, CONSTANT
    ) -> None:
        self.frame = frame
        self.property_path = property_path
        self.value = value
        self.interpolation = interpolation

    def to_mapping(self) -> dict[str, Any]:
        return {
            "frame": self.frame,
            "property_path": self.property_path,
            "value": self.value,
            "interpolation": self.interpolation,
        }


class Constraint:
    """Une contrainte d'animation : type, cible, influence, propriétés.

    Les contraintes relient des propriétés entre objets (Track To, Copy Location...).
    """

    def __init__(
        self,
        type: str,  # type de contrainte : TRACK_TO, COPY_LOCATION, IK...
        target: str | None = None,  # nom de l'objet cible
        influence: float = 1.0,  # influence de la contrainte (0.0 à 1.0)
        properties: dict[str, Any] | None = None,  # propriétés spécifiques à la contrainte
    ) -> None:
        self.type = type
        self.target = target
        self.influence = influence
        self.properties = properties or {}

    def to_mapping(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "target": self.target,
            "influence": self.influence,
            "properties": self.properties,
        }


class AnimationClip:
    """Un clip d'animation pour un personnage dans un plan.

    Contient les keyframes, contraintes et métadonnées pour animer
    un personnage spécifique durant un plan du storyboard.
    """

    def __init__(
        self,
        character_name: str,  # nom du personnage animé
        shot_index: int,  # index du plan dans le storyboard
        keyframes: list[Keyframe] | None = None,  # points clés de l'animation
        constraints: list[Constraint] | None = None,  # contraintes d'animation
        lip_sync: bool = False,  # animation de synchronisation labiale activée
        expression: str | None = None,  # expression faciale dominante
        duration: float = 0.0,  # durée du clip en secondes
        fps: int = 24,  # images par seconde
    ) -> None:
        self.character_name = character_name
        self.shot_index = shot_index
        self.keyframes = keyframes or []
        self.constraints = constraints or []
        self.lip_sync = lip_sync
        self.expression = expression
        self.duration = duration
        self.fps = fps

    def to_mapping(self) -> dict[str, Any]:
        return {
            "character_name": self.character_name,
            "shot_index": self.shot_index,
            "keyframes": [k.to_mapping() for k in self.keyframes],
            "constraints": [c.to_mapping() for c in self.constraints],
            "lip_sync": self.lip_sync,
            "expression": self.expression,
            "duration": self.duration,
            "fps": self.fps,
        }


class AnimationResult:
    """Résultat de la génération d'animations : liste de clips.

    Produit par AnimatorAgent. Contient tous les clips d'animation
    pour tous les personnages de la scène.
    """

    def __init__(self, clips: list[AnimationClip]) -> None:  # clips d'animation
        self.clips = clips

    def to_mapping(self) -> dict[str, Any]:
        return {"clips": [c.to_mapping() for c in self.clips]}


class ReviewReport:
    """Rapport de revue finale : score, verdict, issues par domaine.

    Produit par ReviewAgent. Évalue la qualité globale de la production
    sur plusieurs axes (continuité, visuel, audio, technique).
    """

    def __init__(
        self,
        score: int = 0,  # score global (0 à 100)
        passed: bool = False,  # True si la production est acceptable
        continuity_issues: list[str] | None = None,  # problèmes de continuité
        visual_issues: list[str] | None = None,  # problèmes visuels
        audio_issues: list[str] | None = None,  # problèmes audio
        technical_issues: list[str] | None = None,  # problèmes techniques
        brief_alignment: float = 0.0,  # adéquation au brief (0.0 à 1.0)
        notes: str = "",  # notes générales
        recommendations: list[str] | None = None,  # recommandations d'amélioration
    ) -> None:
        self.score = score
        self.passed = passed
        self.continuity_issues = continuity_issues or []
        self.visual_issues = visual_issues or []
        self.audio_issues = audio_issues or []
        self.technical_issues = technical_issues or []
        self.brief_alignment = brief_alignment
        self.notes = notes
        self.recommendations = recommendations or []

    def to_mapping(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "continuity_issues": self.continuity_issues,
            "visual_issues": self.visual_issues,
            "audio_issues": self.audio_issues,
            "technical_issues": self.technical_issues,
            "brief_alignment": self.brief_alignment,
            "notes": self.notes,
            "recommendations": self.recommendations,
        }


@dataclass
class AudioPlan:
    """Plan audio d'une séquence : ambiances, musique, effets, voix.

    Produit par AudioAgent. Définit la structure audio globale
    avant le mixage final.
    """

    mood: str = ""  # ambiance sonore dominante
    music_theme: str = ""  # thème musical principal
    tempo: float = 0.0  # tempo en BPM
    volume_music: float = 0.4  # volume relatif de la musique (0.0 à 1.0)
    sfx_events: list[str] = field(default_factory=list)  # effets sonores à produire
    voice_tracks: list[str] = field(default_factory=list)  # pistes vocales à produire

    def to_mapping(self) -> dict[str, Any]:
        return {
            "mood": self.mood,
            "music_theme": self.music_theme,
            "tempo": self.tempo,
            "sfx": len(self.sfx_events),
            "voice_tracks": len(self.voice_tracks),
        }


@dataclass
class MusicCue:
    """Un segment musical timed : beat, durée, instruments, dynamique.

    Représente un moment précis de la bande-son musicale.
    """

    start_time: float = 0.0  # timestamp de début en secondes
    end_time: float = 0.0  # timestamp de fin en secondes
    description: str = ""  # description du segment musical
    theme: str = ""  # thème musical associé
    tempo: int = 120  # tempo en BPM
    key: str = "C"  # tonalité (C, Dm, G#...)
    instruments: list[str] = field(default_factory=list)  # instruments utilisés
    dynamics: str = "mf"  # dynamique : pp, p, mp, mf, f, ff
    mood: str = ""  # ambiance émotionnelle
    adaptive: bool = False  # True si la musique s'adapte à l'action

    def to_mapping(self) -> dict[str, Any]:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "description": self.description,
            "theme": self.theme,
            "tempo": self.tempo,
            "key": self.key,
            "instruments": self.instruments,
            "dynamics": self.dynamics,
            "mood": self.mood,
            "adaptive": self.adaptive,
        }


@dataclass
class MusicPlan:
    """Plan musical complet : thèmes, leitmotivs, cues, orchestration.

    Produit par MusicComposerAgent. Contient toute la structure musicale
    pour la production.
    """

    main_theme: str = ""  # thème musical principal
    leitmotifs: dict[str, str] = field(default_factory=dict)  # leitmotivs par personnage/thème
    cues: list[MusicCue] = field(default_factory=list)  # séquence de cues musicaux
    total_duration: float = 0.0  # durée totale en secondes
    genre: str = ""  # genre musical : orchestral, electronic, ambient...
    instrumentation: str = "hybrid"  # orchestration : orchestral, electronic, hybrid, acoustic
    tempo_range: tuple[int, int] = (80, 140)  # plage de tempo (min, max) en BPM
    key_signature: str = "C major"  # tonalité globale
    silence_cues: list[float] = field(default_factory=list)  # timestamps de silence

    def to_mapping(self) -> dict[str, Any]:
        return {
            "main_theme": self.main_theme,
            "leitmotifs": self.leitmotifs,
            "cues": [c.to_mapping() for c in self.cues],
            "total_duration": self.total_duration,
            "genre": self.genre,
            "instrumentation": self.instrumentation,
            "tempo_range": list(self.tempo_range),
            "key_signature": self.key_signature,
            "silence_cues": self.silence_cues,
        }


@dataclass
class SoundLayer:
    """Une couche sonore dans le mix : type, volume, pan, reverb, EQ.

    Représente une piste individuelle du mixage sonore.
    """

    name: str = ""  # nom de la couche
    layer_type: str = "ambience"  # type : ambience, foley, sfx, dialogue, music
    events: list[dict[str, Any]] = field(default_factory=list)  # événements sonores
    volume: float = 0.5  # volume relatif (0.0 à 1.0)
    pan: float = 0.0  # panoramique (-1.0 gauche, 0.0 centre, 1.0 droite)
    reverb: str = ""  # paramètres de réverbération
    eq_notes: str = ""  # notes d'égalisation

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "layer_type": self.layer_type,
            "events": self.events,
            "volume": self.volume,
            "pan": self.pan,
            "reverb": self.reverb,
            "eq_notes": self.eq_notes,
        }


@dataclass
class SoundDesignPlan:
    """Plan de conception sonore : couches, foley, ambiances, paramètres audio.

    Produit par SoundDesignerAgent. Contient les spécifications détaillées
    pour le mixage audio final.
    """

    layers: list[SoundLayer] = field(default_factory=list)  # couches sonores
    spatial_format: str = "stereo"  # format spatial : stereo, 5.1, ambisonics
    sample_rate: int = 48000  # fréquence d'échantillonnage en Hz
    bit_depth: int = 24  # profondeur de bits
    master_loudness: float = -14.0  # loudness cible en LUFS
    dynamic_range: float = 12.0  # plage dynamique en dB
    monitoring: str = "stereo"  # type de monitoring : stereo, headphones, 5.1

    def to_mapping(self) -> dict[str, Any]:
        return {
            "layers": [layer.to_mapping() for layer in self.layers],
            "spatial_format": self.spatial_format,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
            "master_loudness": self.master_loudness,
            "dynamic_range": self.dynamic_range,
            "monitoring": self.monitoring,
        }


@dataclass
class AudioMaster:
    """Mix final assemblé : piste unique versionnée et inspectable.

    Représente le fichier audio master résultant du mixage.
    """

    path: str = ""  # chemin vers le fichier audio master
    duration: float = 0.0  # durée en secondes
    channels: int = 1  # nombre de canaux (1=mono, 2=stereo, 6=5.1)
    sample_rate: int = 44100  # fréquence d'échantillonnage en Hz
    language: str = ""  # langue principale de la piste vocale


@dataclass
class CompositeSpec:
    """Passes et étalonnage du compositing post-rendu.

    Produit par CompositingAgent. Définit les passes de rendu à combiner
    et l'étalonnage couleur final.
    """

    passes: list[str] = field(default_factory=lambda: ["diffuse", "direct", "shadow", "mist"])  # passes de rendu
    grade: str = "balanced"  # étalonnage : balanced, warm, cold, cinematic, vintage
    effects: list[str] = field(default_factory=list)  # effets post-rendu : bloom, glare, vignette
    output_format: str = "exr"  # format de sortie : exr, png, tiff

    def to_mapping(self) -> dict[str, Any]:
        return {
            "passes": len(self.passes),
            "grade": self.grade,
            "effects": self.effects,
            "output_format": self.output_format,
        }


@dataclass
class LanguagePackage:
    """Un lot de localisation complet pour une langue cible.

    Contient les dialogues traduits, sous-titres, voix et métadonnées
    pour une langue spécifique.
    """

    language: str  # langue cible (code ISO : fr, en, wo, ar...)
    dialogues: list[str] = field(default_factory=list)  # dialogues traduits
    subtitles_path: str = ""  # chemin vers le fichier de sous-titres (.srt)
    voice_path: str = ""  # chemin vers la piste vocale générée
    metadata: dict[str, str] = field(default_factory=dict)  # métadonnées de localisation
    interface: dict[str, str] = field(default_factory=dict)  # traductions de l'interface
    languages: list[str] = field(default_factory=list)  # langues impliquées (cible + sources)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "languages": len(self.languages),
            "dialogues": len(self.dialogues),
            "subtitles_path": self.subtitles_path,
            "voice_path": self.voice_path,
            "interface_keys": len(self.interface),
        }
