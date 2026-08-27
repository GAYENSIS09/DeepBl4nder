"""Agents DeepBlender : sous-classes directes de nooa.Agent.

Aucun framework agentique propriétaire : le runtime, le contexte, les
événements, la mémoire et le tracing sont ceux de NOOA (P5).
"""

from __future__ import annotations

from deepblender.agents.animator import AnimatorAgent
from deepblender.agents.audio import AudioAgent
from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.agents.blender import BlenderAgent
from deepblender.agents.char import CharacterDesignerAgent
from deepblender.agents.comp import CompositingAgent
from deepblender.agents.director import DirectorAgent
from deepblender.agents.env import EnvironmentArtistAgent
from deepblender.agents.loc import LocalizationAgent
from deepblender.agents.music import MusicComposerAgent
from deepblender.agents.qa import QAAgent
from deepblender.agents.review import ReviewAgent
from deepblender.agents.sfx import SoundDesignerAgent
from deepblender.agents.story import StoryAgent
from deepblender.agents.board import StoryboardAgent
from deepblender.agents.ue5 import UE5Agent

__all__ = [
    "AnimatorAgent",
    "AudioAgent",
    "BaseAgent",
    "BlenderAgent",
    "CharacterDesignerAgent",
    "CompositingAgent",
    "DefaultsMixin",
    "DirectorAgent",
    "EnvironmentArtistAgent",
    "LocalizationAgent",
    "MusicComposerAgent",
    "QAAgent",
    "ReviewAgent",
    "SoundDesignerAgent",
    "StoryAgent",
    "StoryboardAgent",
    "UE5Agent",
]
