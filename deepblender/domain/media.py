"""Specs structurées du pipeline média : audio, compositing et langues.

Couvre les étapes 14-16 du pipeline audiovisuel (doc 03) : compositing,
audio (sound design, musique, voix) et localisation (dialogues, sous-titres,
métadonnées, interface).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioPlan:
    """Plan audio d'une séquence : ambiances, musique, effets, voix."""

    mood: str = ""
    music_theme: str = ""
    tempo: float = 0.0
    volume_music: float = 0.4
    sfx_events: list[str] = field(default_factory=list)
    voice_tracks: list[str] = field(default_factory=list)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "mood": self.mood,
            "music_theme": self.music_theme,
            "tempo": self.tempo,
            "sfx": len(self.sfx_events),
            "voice_tracks": len(self.voice_tracks),
        }


@dataclass
class AudioMaster:
    """Mix final assemblé : piste unique versionnée et inspectable."""

    path: str = ""
    duration: float = 0.0
    channels: int = 1
    sample_rate: int = 44100
    language: str = ""


@dataclass
class CompositeSpec:
    """Passes et étalonnage du compositing post-rendu."""

    passes: list[str] = field(default_factory=lambda: ["diffuse", "direct", "shadow", "mist"])
    grade: str = "balanced"
    effects: list[str] = field(default_factory=list)
    output_format: str = "exr"

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

    ``language`` est la langue cible du lot ; ``languages`` liste toutes les
    langues impliquées (cible + langues d'origine des répliques), ce qui permet
    de représenter un personnage multilingue sans perte d'information.
    """

    language: str
    dialogues: list[str] = field(default_factory=list)
    subtitles_path: str = ""
    voice_path: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    interface: dict[str, str] = field(default_factory=dict)
    languages: list[str] = field(default_factory=list)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "languages": len(self.languages),
            "dialogues": len(self.dialogues),
            "subtitles_path": self.subtitles_path,
            "voice_path": self.voice_path,
            "interface_keys": len(self.interface),
        }
