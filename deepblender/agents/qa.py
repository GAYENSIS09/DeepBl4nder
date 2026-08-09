"""QAAgent : évalue un artifact produit contre sa spec (NOOA Agent).

Le QA couvre quatre niveaux (Roadmap B §15) : technique, visuel, continuité et
sémantique. Les contrôles déterministes sont du Python pur ; l'appréciation
sémantique (brief vs rendu) utilise CodeActStrategy avec skills qa, continuity.

Utilise les skills : qa, continuity, feasibility, cinematography, composition.
"""

from __future__ import annotations

from typing import Any

from nooa import Agent, CodeActStrategy, strategy
from nooa.skill import TextSkill

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.qa import QAReport, Issue, IssueKind
from deepblender.domain.scene import SceneSpec
from deepblender.skills.registry import SkillRegistry


class QAAgent(BaseAgent, DefaultsMixin):
    """You are a production quality agent.

    You assess a rendered artifact against its typed scene specification and
    the original creative brief.

    ## Skills available (progressive disclosure)
    - qa: technical checks, visual assessment, semantic comparison, scoring
    - continuity: shot matching, eye-line, screen direction, temporal consistency
    - feasibility: render time, memory, polygon count, shader complexity
    - cinematography: camera work quality, framing, movement
    - composition: visual balance, rule of thirds, depth

    ## Rules
    - Apply deterministic technical checks first (file exists, format, metadata).
    - Use semantic judgment to compare the brief with the render.
    - Always produce a typed QAReport with a score, issues and recommendations.
    - A failing report must point to the affected production step so the
      revision can be targeted, never restarted from scratch.
    - Output MUST be a valid QAReport (validated via output_model).
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy())
    async def assess(self, spec: SceneSpec, artifact_path: str) -> QAReport:
        """Assess the rendered artifact against the scene spec.

        Steps:
        1. Load core skill summaries
        2. Run deterministic technical checks (file exists, readable, metadata)
        3. Load qa, continuity skills for assessment criteria
        4. If visual artifact (image/video): analyze against spec (camera, lighting, composition)
        5. Compare brief intent with rendered result (semantic check)
        6. Produce QAReport with score (0-1), issues (typed with step), recommendations
        7. Issues MUST include step: "director" | "blender" | "audio" | "compositing" | "localization"
        """
        self._load_core_skills()
        self._load_skills("qa", "continuity", "feasibility")

        # CodeActStrategy generates assessment code, output validated as QAReport
        ...

    def technical_check(self, artifact_path: str) -> list[Issue]:
        """Deterministic technical checks on an artifact path."""
        issues: list[Issue] = []
        if not artifact_path:
            issues.append(Issue(kind=IssueKind.TECHNICAL, message="artifact path is empty", step="blender"))
        return issues
