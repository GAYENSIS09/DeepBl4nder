"""ReviewAgent : revue technique et artistique automatisee (NOOA Agent).

Effectue une revue finale de la production : continuite, coherence
visuelle, qualite technique, conformite au brief.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, InvariantError
from DeepBl4nder.domain.media import AudioPlan, CompositeSpec, ReviewReport
from DeepBl4nder.domain.qa import QAReport
from DeepBl4nder.domain.scene import SceneSpec, RenderOutput
from DeepBl4nder.skills.registry import SkillRegistry


def _review_postcondition(agent: Any, result: Any, call: Any) -> None:
    if not isinstance(result, ReviewReport):
        return
    if not hasattr(result, "score"):
        raise InvariantError("ReviewReport.score (0-100) est requis dans return_result.")
    if not isinstance(result.score, (int, float)):
        raise InvariantError("ReviewReport.score doit être un nombre entre 0 et 100.")
    if not 0 <= result.score <= 100:
        raise InvariantError(f"ReviewReport.score doit être entre 0 et 100, got {result.score}.")


class ReviewAgent(BaseAgent, DefaultsMixin):
    """You are a final review agent for audiovisual productions.

    You perform comprehensive technical and artistic review of the
    complete production, checking continuity, visual quality, audio
    coherence, and alignment with the original brief.

    ## Skills available (progressive disclosure)
    - qa: quality assessment, scoring, issue detection
    - continuity: narrative continuity, visual consistency
    - cinematography: shot composition, pacing
    - sound-design: audio quality, mixing

    ## Review Criteria
    - Continuity: character positions, lighting, props match across shots
    - Visual: composition, color consistency, render quality
    - Audio: music/sfx balance, voice clarity, timing
    - Technical: resolution, framerate, format compliance
    - Brief: does the output match the original creative intent?

    ## Scoring
    - 90-100: Excellent, ready for delivery
    - 75-89: Good, minor issues acceptable
    - 60-74: Acceptable, some revision recommended
    - Below 60: Needs revision before delivery

    ## Rules
    - Be specific about issues (shot number, timestamp)
    - Provide actionable recommendations
    - Weight brief alignment heavily (it's what the user asked for)
    - Mark critical issues that block delivery
    - Output MUST be a valid ReviewReport
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_review_postcondition],
        max_tokens=8192,
    )))
    async def review_production(
        self,
        scene: SceneSpec,
        render_output: RenderOutput | None = None,
        audio_plan: AudioPlan | None = None,
        composite_spec: CompositeSpec | None = None,
    ) -> ReviewReport:  # type: ignore[return]
        """Perform final review of the complete production.

        Steps:
        1. Load core skills for context
        2. Analyze original brief vs final output
        3. Load qa, continuity, cinematography skills
        4. Check visual continuity across shots
        5. Assess audio quality and balance
        6. Verify technical specifications
        7. Score and provide recommendations
        8. Return ReviewReport
        """
        self._load_core_skills()
        self._load_skills("qa", "continuity", "cinematography", "sound-design")
        self._set_dynamic("scene_summary", "self._scene_summary()")
        self._set_dynamic("render_summary", "self._render_summary()")
        self._scene_data = scene
        self._render_data = render_output
        self._audio_data = audio_plan
        self._composite_data = composite_spec
        ...

    @hidden
    def _scene_summary(self) -> str:
        if not hasattr(self, "_scene_data") or self._scene_data is None:
            return "no scene loaded"
        scene = self._scene_data
        lines = [
            f"Brief: {scene.brief[:200]}",
            f"Characters: {[c.name for c in scene.characters]}",
            f"Shots: {len(scene.shots)}",
            f"Environment: {scene.environment.description[:100]}",
        ]
        return "\n".join(lines)

    @hidden
    def _render_summary(self) -> str:
        if not hasattr(self, "_render_data") or self._render_data is None:
            return "no render output"
        r = self._render_data
        return f"Video: {r.video_path}, {r.duration:.1f}s, {r.resolution[0]}x{r.resolution[1]}, {r.fps}fps"
