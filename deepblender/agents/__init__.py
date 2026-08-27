"""Agents DeepBl4nder : sous-classes directes de nooa.Agent.

Aucun framework agentique propriétaire : le runtime, le contexte, les
événements, la mémoire et le tracing sont ceux de NOOA (P5).
"""

from __future__ import annotations

from DeepBl4nder.agents.animator import AnimatorAgent
from DeepBl4nder.agents.audio import AudioAgent
from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin
from DeepBl4nder.agents.blender import BlenderAgent
from DeepBl4nder.agents.char import CharacterDesignerAgent
from DeepBl4nder.agents.comp import CompositingAgent
from DeepBl4nder.agents.director import DirectorAgent
from DeepBl4nder.agents.env import EnvironmentArtistAgent
from DeepBl4nder.agents.loc import LocalizationAgent
from DeepBl4nder.agents.music import MusicComposerAgent
from DeepBl4nder.agents.qa import QAAgent
from DeepBl4nder.agents.review import ReviewAgent
from DeepBl4nder.agents.sfx import SoundDesignerAgent
from DeepBl4nder.agents.story import StoryAgent
from DeepBl4nder.agents.board import StoryboardAgent
from DeepBl4nder.agents.ue5 import UE5Agent

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
