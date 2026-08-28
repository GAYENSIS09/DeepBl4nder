"""StoryboardAgent : transforme une StorySpec en StoryboardSpec (découpage en plans)."""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, storyboard_spec_postcondition
from DeepBl4nder.domain.narrative import StorySpec, StoryboardSpec
from DeepBl4nder.skills.registry import SkillRegistry


class StoryboardAgent(BaseAgent, DefaultsMixin):
    """You are a storyboard artist and visual storyteller.

    You transform a structured StorySpec into a shot-by-shot StoryboardSpec:
    - Each shot has: index, description, duration, camera angle/movement
    - Characters present, action, dialogue references
    - Transitions between shots
    - Visual notes for the director

    ## Skills available (progressive disclosure)
    - cinematography: camera angles, movement, composition rules
    - storyboard: beat boards, thumbnails, animatic timing
    - composition: rule of thirds, leading lines, depth, framing

    ## Rules
    - Output MUST be a valid StoryboardSpec
    - Shot count and durations must match story pacing
    - Camera choices must serve the narrative emotion
    - Transitions must be motivated (not decorative)
    - Total duration should match target from brief

    ## Revision
    - On QA revision, ``revision_feedback`` contains issues to address
    - Adjust specific shots, don't redesign entire board
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[storyboard_spec_postcondition],
        max_tokens=16384,
    )))
    async def plan_storyboard(self, story: StorySpec) -> StoryboardSpec:  # type: ignore[return]
        """Generate a complete StoryboardSpec from a StorySpec."""
        self._load_core_skills()
        self._load_skills("cinematography", "storyboard", "composition")
        
        self._set_context("story", str(story.to_mapping()))
        ...


    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[storyboard_spec_postcondition],
        max_tokens=16384,
    )))
    async def revise_storyboard(self, storyboard: StoryboardSpec, revision_feedback: str) -> StoryboardSpec:  # type: ignore[return]
        """Revise a StoryboardSpec based on QA feedback."""
        self._load_core_skills()
        self._load_skills("cinematography", "storyboard")
        self.context["revision_feedback"] = revision_feedback
        self._set_context("current_storyboard", str(storyboard.to_mapping()))
        ...