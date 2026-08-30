"""DeepBl4nder brand palette for the TUI.

Extracted from ``public/logo.svg``: a near-black ``#0A0A0A`` background, an
acid-green ``#AAFF00`` accent (gradient to ``#88CC00``), white text and a
muted gray for secondary information.
"""

from __future__ import annotations

# Brand accents (from the logo gradient).
ACCENT = "#AAFF00"
ACCENT_2 = "#88CC00"

# Surfaces (near-black base from the logo).
BACKGROUND = "#0A0A0A"
SURFACE = "#121212"
PANEL = "#171717"
BORDER = "#262626"

TEXT = "#F2F2F2"
TEXT_MUTED = "#A0A098"
TEXT_DIM = "#7A7A72"

SUCCESS = "#AAFF00"
ERROR = "#FF5C57"
WARNING = "#E6C229"
INFO = "#56B6C2"

# Actor accent colors used to distinguish agents in the live stream.
ACTOR_COLORS: dict[str, str] = {
    "story": "#AAFF00",
    "storyboard": "#88CC00",
    "director": "#E6C229",
    "character_designer": "#C792EA",
    "environment_artist": "#56B6C2",
    "blender": "#61AFEF",
    "qa": "#FF5C57",
    "animator": "#FFAB70",
    "audio": "#F78C6C",
    "music_composer": "#D19A66",
    "sound_designer": "#82AAFF",
    "localization": "#89CA78",
    "compositing": "#B294BB",
    "review": "#EF596F",
    "ue5": "#7FC8FF",
}

ACTOR_LABELS: dict[str, str] = {
    "story": "Story",
    "storyboard": "Storyboard",
    "director": "Director",
    "character_designer": "Character Design",
    "environment_artist": "Environment",
    "blender": "Blender",
    "qa": "QA",
    "animator": "Animation",
    "audio": "Audio",
    "music_composer": "Music",
    "sound_designer": "Sound Design",
    "localization": "Localization",
    "compositing": "Compositing",
    "review": "Review",
    "ue5": "Unreal Engine",
}