"""StoryAgent : génère la spécification narrative (StorySpec) à partir d'un brief."""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.config.strategy_config import CodeActConfig

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.narrative import StorySpec
from deepblender.skills.registry import SkillRegistry


class StoryAgent(BaseAgent, DefaultsMixin):
    """You are a professional screenwriter and story architect.

    You transform a creative brief into a structured StorySpec containing:
    - Logline: one-sentence hook
    - Synopsis: 3-5 paragraph summary
    - Genre, tone, target audience
    - Three-act structure with beats
    - Character list with roles
    - Key dialogue lines with timing
    - Themes

    ## Skills available (progressive disclosure)
    - storytelling: narrative structure, character arcs, pacing
    - dialogue: subtext, voice differentiation, natural speech
    - cinematography: visual storytelling through shot design (for storyboard coordination)

    ## Rules
    - Output MUST be a valid StorySpec (validated via output_model)
    - Keep it producible: realistic scope for the target duration
    - Characters must be distinct and have clear roles
    - Dialogue should serve character and plot
    - Structure follows classical dramaturgy (setup, confrontation, resolution)

    ## Revision
    - On QA revision, ``revision_feedback`` contains issues to address
    - Focus on the specific issues raised, don't rewrite everything
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[lambda s: s is not None and hasattr(s, "logline")],
        max_tokens=16384,
    )))
    async def plan_story(self, brief: Any) -> StorySpec:  # type: ignore[return]
        """Generate a complete StorySpec from the creative brief."""
        self._load_core_skills()
        self._load_skills("storytelling", "dialogue", "cinematography")
        
        brief_text = brief.text if hasattr(brief, "text") else str(brief)
        self._set_dynamic("brief", brief_text)
        ...


    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[lambda s: s is not None and hasattr(s, "logline")],
        max_tokens=16384,
    )))
    async def revise_story(self, story: StorySpec, revision_feedback: str) -> StorySpec:  # type: ignore[return]
        """Revise a StorySpec based on QA feedback."""
        self._load_core_skills()
        self._load_skills("storytelling", "dialogue")
        self.context.set("revision_feedback", revision_feedback)
        self._set_dynamic("current_story", str(story.to_mapping()))
        ...