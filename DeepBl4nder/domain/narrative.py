"""Objets domaine : StorySpec, StoryboardSpec (narration et découpage).

Structures narratives pour le pipeline de production vidéo/animation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from DeepBl4nder.domain.utils import new_id as _new_id


def _plain(value: Any) -> Any:
    """Sérialise dataclass OU dict brut tel quel.

    NOOA construit les specs sans conversion récursive : quand le modèle
    renvoie du JSON, les listes imbriquées (acts, shots, dialogues… peuvent
    contenir des dicts au lieu des dataclass du domaine. Les sérialiseurs
    doivent tolérer les deux.
    """
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


@dataclass
class StoryBeat:
    """Un temps fort narratif (beat) dans l'histoire.

    Représente un moment clé de l'intrigue : une révélation, un conflit,
    une resolution. Les beats constituent la structure granulaire de l'histoire.
    """

    description: str  # description du beat narratif
    characters: list[str] = field(default_factory=list)  # noms des personnages impliqués
    location: str = ""  # lieu où se déroule le beat
    mood: str = ""  # ambiance émotionnelle : joyeux, tendu, mélancolique...
    duration_estimate: float = 0.0  # durée estimée en secondes


@dataclass
class Act:
    """Un acte de l'histoire (structure en 3 actes classique).

    Chaque acte contient une séquence de beats qui construisent l'intrigue.
    """

    name: str  # nom de l'acte (ex: "Acte 1 - Exposition")
    beats: list[StoryBeat] = field(default_factory=list)  # séquence de beats
    order: int = 0  # position dans la structure (0, 1, 2...)


@dataclass
class DialogueLine:
    """Une ligne de dialogue : personnage, texte, émotion, langue.

    Représente une réplique individuelle avec ses métadonnées.
    """

    character: str  # nom du personnage qui parle
    text: str  # texte de la réplique
    emotion: str = ""  # émotion du personnage : neutre, colère, joie, tristesse...
    language: str = "fr"  # langue de la réplique (code ISO)
    start_time: float = 0.0  # timestamp de début en secondes
    end_time: float = 0.0  # timestamp de fin en secondes


@dataclass
class StorySpec:
    """Spécification complète de l'histoire : synopsis, structure, dialogues.

    Produite par StoryAgent. Contient toute l'information narrative nécessaire
    pour le reste du pipeline (storyboard, direction, audio...).
    """

    logline: str = ""  # résumé en une phrase (accroche)
    synopsis: str = ""  # résumé détaillé de l'histoire
    genre: str = ""  # genre : drame, comédie, thriller, animation, documentaire...
    tone: str = ""  # ton : sérieux, léger, satirique, dramatique...
    target_audience: str = ""  # public cible : enfants, adultes, famille...
    acts: list[Act] = field(default_factory=list)  # structure en actes
    characters: list[str] = field(default_factory=list)  # noms des personnages principaux
    dialogues: list[DialogueLine] = field(default_factory=list)  # toutes les répliques
    themes: list[str] = field(default_factory=list)  # thèmes explorés
    id: str = field(default_factory=_new_id)  # identifiant unique
    schema_version: int = 1  # version du schéma

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "logline": self.logline,
            "synopsis": self.synopsis,
            "genre": self.genre,
            "tone": self.tone,
            "target_audience": self.target_audience,
            "acts": [_plain(a) for a in self.acts],
            "characters": self.characters,
            "dialogues": [_plain(d) for d in self.dialogues],
            "themes": self.themes,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StorySpec":
        acts = []
        for act_data in data.get("acts", []):
            beats = [
                StoryBeat(
                    description=b.get("description", ""),
                    characters=b.get("characters", []),
                    location=b.get("location", ""),
                    mood=b.get("mood", ""),
                    duration_estimate=b.get("duration_estimate", 0.0),
                )
                for b in act_data.get("beats", [])
            ]
            acts.append(Act(name=act_data.get("name", ""), beats=beats, order=act_data.get("order", 0)))

        dialogues = [
            DialogueLine(
                character=d.get("character", ""),
                text=d.get("text", ""),
                emotion=d.get("emotion", ""),
                language=d.get("language", "fr"),
                start_time=d.get("start_time", 0.0),
                end_time=d.get("end_time", 0.0),
            )
            for d in data.get("dialogues", [])
        ]

        return cls(
            logline=data.get("logline", ""),
            synopsis=data.get("synopsis", ""),
            genre=data.get("genre", ""),
            tone=data.get("tone", ""),
            target_audience=data.get("target_audience", ""),
            acts=acts,
            characters=data.get("characters", []),
            dialogues=dialogues,
            themes=data.get("themes", []),
            schema_version=data.get("schema_version", 1),
        )


@dataclass
class StoryboardShot:
    """Un plan du storyboard : description, caméra, personnages, action.

    Représente la vision visuelle d'un plan spécifique du storyboard.
    Contient les instructions pour la caméra, les personnages et l'action.
    """

    index: int  # position du plan dans le storyboard (0-based)
    description: str = ""  # description visuelle du plan
    duration: float = 5.0  # durée en secondes
    camera_angle: str = "medium"  # angle : wide, medium, closeup, extreme_closeup
    camera_movement: str = "static"  # mouvement : static, pan, tilt, dolly, crane, handheld
    characters: list[str] = field(default_factory=list)  # personnages visibles
    action: str = ""  # description de l'action du plan
    dialogue_refs: list[int] = field(default_factory=list)  # indices dans StorySpec.dialogues
    transition: str = "cut"  # transition vers le plan suivant : cut, fade, dissolve, wipe
    visual_notes: str = ""  # notes visuelles supplémentaires
    order: int = 0  # ordre dans le storyboard


@dataclass
class StoryboardSpec:
    """Spécification complète du storyboard : liste ordonnée de plans.

    Produite par StoryboardAgent. Convertit la narrative (StorySpec) en
    instructions visuelles pour le pipeline de production.
    """

    shots: list[StoryboardShot] = field(default_factory=list)  # plans du storyboard
    total_duration: float = 0.0  # durée totale en secondes
    id: str = field(default_factory=_new_id)  # identifiant unique
    schema_version: int = 1  # version du schéma

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "shots": [_plain(s) for s in self.shots],
            "total_duration": self.total_duration,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StoryboardSpec":
        shots = [
            StoryboardShot(
                index=s.get("index", i),
                description=s.get("description", ""),
                duration=s.get("duration", 5.0),
                camera_angle=s.get("camera_angle", "medium"),
                camera_movement=s.get("camera_movement", "static"),
                characters=s.get("characters", []),
                action=s.get("action", ""),
                dialogue_refs=s.get("dialogue_refs", []),
                transition=s.get("transition", "cut"),
                visual_notes=s.get("visual_notes", ""),
                order=s.get("order", i),
            )
            for i, s in enumerate(data.get("shots", []))
        ]
        return cls(
            shots=shots,
            total_duration=data.get("total_duration", sum(s.duration for s in shots)),
            schema_version=data.get("schema_version", 1),
        )
