"""Objets domaine : StorySpec, StoryboardSpec (narration et découpage)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any
from uuid import uuid4


def _new_id() -> str:
    return uuid4().hex


def _plain(value: Any) -> Any:
    """Sérialise dataclass OU dict brut tel quel.

    NOOA construit les specs sans conversion récursive : quand le modèle
    renvoie du JSON, les listes imbriquées (acts, shots, dialogues…) peuvent
    contenir des dicts au lieu des dataclass du domaine. Les sérialiseurs
    doivent tolérer les deux.
    """
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


@dataclass
class StoryBeat:
    """Un temps fort narratif (beat) dans l'histoire."""

    description: str
    characters: list[str] = field(default_factory=list)
    location: str = ""
    mood: str = ""
    duration_estimate: float = 0.0  # en secondes


@dataclass
class Act:
    """Un acte de l'histoire (structure en 3 actes classique)."""

    name: str
    beats: list[StoryBeat] = field(default_factory=list)
    order: int = 0


@dataclass
class DialogueLine:
    """Une ligne de dialogue."""

    character: str
    text: str
    emotion: str = ""
    language: str = "fr"
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class StorySpec:
    """Spécification complète de l'histoire (synopsis, structure, dialogues)."""

    logline: str = ""
    synopsis: str = ""
    genre: str = ""
    tone: str = ""
    target_audience: str = ""
    acts: list[Act] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)
    dialogues: list[DialogueLine] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    id: str = field(default_factory=_new_id)
    schema_version: int = 1

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
    """Un plan du storyboard (découpage visuel)."""

    index: int
    description: str = ""
    duration: float = 5.0
    camera_angle: str = "medium"  # wide, medium, closeup, extreme_closeup
    camera_movement: str = "static"  # static, pan, tilt, dolly, crane, handheld
    characters: list[str] = field(default_factory=list)
    action: str = ""
    dialogue_refs: list[int] = field(default_factory=list)  # indices dans StorySpec.dialogues
    transition: str = "cut"  # cut, fade, dissolve, wipe
    visual_notes: str = ""
    order: int = 0


@dataclass
class StoryboardSpec:
    """Spécification complète du storyboard (liste ordonnée de plans)."""

    shots: list[StoryboardShot] = field(default_factory=list)
    total_duration: float = 0.0
    id: str = field(default_factory=_new_id)
    schema_version: int = 1

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