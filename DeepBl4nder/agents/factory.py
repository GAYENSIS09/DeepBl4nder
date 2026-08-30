"""Factory centralisée pour construire les agents NOOA.

Ce module est la source unique de création de la crew d'agents.
Il est importé par le TUI et tout autre consommateur, éliminant
la dépendance à l'ancien package api/.
"""

from __future__ import annotations

from typing import Any

from DeepBl4nder.agents import (
    AnimatorAgent,
    AudioAgent,
    BlenderAgent,
    CharacterDesignerAgent,
    CompositingAgent,
    DirectorAgent,
    EnvironmentArtistAgent,
    LocalizationAgent,
    MusicComposerAgent,
    QAAgent,
    ReviewAgent,
    SoundDesignerAgent,
    StoryAgent,
    StoryboardAgent,
    BaseAgent
)
from DeepBl4nder.llm import build_llm


def build_agents() -> tuple[
    BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent, BaseAgent
]:
    """Construit les 14 agents NOOA (story, storyboard, directeur, Blender, QA + post-production)."""
    llm = build_llm()
    return (
        StoryAgent(llm=llm),
        StoryboardAgent(llm=llm),
        DirectorAgent(llm=llm),
        BlenderAgent(llm=llm),
        QAAgent(llm=llm),
        AudioAgent(llm=llm),
        LocalizationAgent(llm=llm),
        CompositingAgent(llm=llm),
        CharacterDesignerAgent(llm=llm),
        AnimatorAgent(llm=llm),
        EnvironmentArtistAgent(llm=llm),
        MusicComposerAgent(llm=llm),
        SoundDesignerAgent(llm=llm),
        ReviewAgent(llm=llm),
    )
