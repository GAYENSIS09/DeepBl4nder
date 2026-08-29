"""QAAgent : évalue un artifact produit contre sa spec (NOOA Agent).

Le QA couvre quatre niveaux (Roadmap B §15) : technique, visuel, continuité et
sémantique. Les contrôles déterministes sont du Python pur ; l'appréciation
sémantique (brief vs rendu) utilise CodeActStrategy avec skills qa, continuity.

Utilise les skills : qa, continuity, feasibility, cinematography, composition.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, PredictStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config import CodeActConfig, PredictConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, InvariantError
from DeepBl4nder.domain.qa import QAReport, Issue, IssueKind
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def _qa_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : un QAReport doit avoir un score valide et des issues typées."""
    from DeepBl4nder.domain.qa import Issue

    if not isinstance(result, QAReport):
        return
    if not (0.0 <= result.score <= 100.0):
        raise InvariantError(
            f"QAReport.score doit être entre 0.0 et 100.0, got {result.score}. "
            "Appelez return_result avec score=75.0 (0.0=échec total, 100.0=parfait)."
        )
    for issue in result.issues:
        if not isinstance(issue, Issue):
            raise InvariantError(
                "Chaque issue doit être un Issue(kind, message, step). "
                "Ex: Issue(kind=IssueKind.TECHNICAL, message='script manquant', step='blender')"
            )
        if not issue.step:
            raise InvariantError(
                f"Issue.step est requis pour '{issue.message}'. "
                'Valeurs: "director", "blender", "qa", "animation", "compositing", "localization"'
            )


class QAAgent(BaseAgent, DefaultsMixin):
    """You are a production quality assurance agent.

    You evaluate a generated artifact against its typed SceneSpec and the
    original creative brief. You produce a QAReport with a score and issues.

    ## Output format — QAReport
    You MUST call return_result with a QAReport:

        return_result(
            passed=True,        # True if score >= 70.0, False otherwise
            score=85.0,         # 0.0 (worst) to 100.0 (best), 70+ = pass
            issues=[],          # list of Issue(kind, message, step)
            recommendations=[]  # list of improvement suggestions
        )

    ## Issue format
    Each issue MUST have a step target for targeted revision:

        Issue(kind=IssueKind.TECHNICAL, message="script has syntax error", step="blender")
        Issue(kind=IssueKind.VISUAL, message="image too dark", step="blender")
        Issue(kind=IssueKind.SEMANTIC, message="mood mismatch with brief", step="director")

    Valid steps: "director", "blender", "qa", "animation", "compositing", "localization"

    ## Skills available (progressive disclosure)
    - qa: technical checks, visual assessment, semantic comparison, scoring
    - continuity: shot matching, eye-line, screen direction, temporal consistency
    - feasibility: render time, memory, polygon count, shader complexity
    - cinematography: camera work quality, framing, movement
    - composition: visual balance, rule of thirds, depth

    ## Rules
    - Apply deterministic technical checks first (file exists, format, metadata).
    - Use semantic judgment to compare the brief with the render.
    - A score >= 70.0 means passed=True. A score < 70.0 means passed=False.
    - Always include at least one recommendation, even if passed=True.
    - Each issue MUST include a step for targeted revision.
    - Never return score=0.0 unless the artifact is completely broken.
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_qa_postcondition],
        max_tokens=8192,
    )))
    async def assess(self, spec: SceneSpec, artifact_path: str, code: str = "") -> QAReport:  # type: ignore[return]
        """Assess the rendered artifact against the scene spec.

        ``artifact_path`` is the host path of the artifact (may not be readable
        from the sandbox) ; ``code`` carries the artifact content when it is a
        script, so the assessment never depends on host filesystem access.

        Steps:
        1. Load core skill summaries
        2. Run deterministic technical checks (file exists, readable, metadata)
        3. Load qa, continuity skills for assessment criteria
        4. If visual artifact (image/video): analyze against spec (camera, lighting, composition)
        5. Compare brief intent with rendered result (semantic check)
        6. Produce QAReport with score (0-100), issues (typed with step), recommendations
        7. Issues MUST include step: "director" | "blender" | "audio" | "compositing" | "localization"
        8. score >= 70.0 means passed=True, score < 70.0 means passed=False
        9. Always include at least one recommendation
        """
        self._load_core_skills()
        self._load_skills("qa", "continuity", "feasibility")

        # CodeActStrategy generates assessment code, output validated as QAReport
        ...

    @strategy(PredictStrategy(config=PredictConfig(
        max_retries=3,
    )))
    async def quick_scan(self, code: str, spec: SceneSpec) -> QAReport:  # type: ignore[return]
        """Fast semantic first-pass scan of a generated script.

        Single LLM turn, no code execution: checks that the script plausibly
        addresses the spec (environment, characters, shots) and returns a typed
        QAReport. Slow, deterministic checks stay in ``technical_check``.
        """
        self._load_core_skills()
        self._load_skill("qa")
        ...

    @hidden
    def technical_check(self, artifact_path: str) -> list[Issue]:
        """Deterministic technical checks on an artifact path."""
        issues: list[Issue] = []
        if not artifact_path:
            issues.append(Issue(kind=IssueKind.TECHNICAL, message="artifact path is empty", step="blender"))
        return issues
