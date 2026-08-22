"""Tests d'intégration : PipelineRunner (brief -> Director -> Blender -> QA)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deepblender.domain.project import Brief
from deepblender.domain.qa import QAReport, Issue, IssueKind
from deepblender.domain.scene import BlenderScript, SceneSpec
from deepblender.production.budget import BudgetTracker
from deepblender.production.runner import PipelineRunner, RunOutcome

VALID_SCRIPT = "import bpy\nscene = bpy.context.scene\nscene.frame_end = 120\n"
INVALID_SCRIPT = "import os\nprint(os.system('whoami'))\n"


class StubDirector:
    async def plan_scene(self, brief: Brief) -> SceneSpec:
        return SceneSpec(brief=brief.text)


class StubBlender:
    def __init__(self, scripts: list[str] | None = None) -> None:
        self.scripts = list(scripts or [])
        self.calls = 0

    async def build_script(self, spec: SceneSpec) -> BlenderScript:
        code = (
            self.scripts[min(self.calls, len(self.scripts) - 1)]
            if self.scripts
            else VALID_SCRIPT
        )
        self.calls += 1
        return BlenderScript(code=code, scene_name="stub_scene")


class StubQA:
    def __init__(self, passed: bool = True) -> None:
        self.passed = passed
        self.received_code: list[str] = []

    async def assess(self, spec: SceneSpec, artifact_path: str, code: str = "") -> QAReport:
        self.received_code.append(code)
        return QAReport(passed=self.passed, score=1.0 if self.passed else 0.0)


async def _run(
    tmp_path: Path,
    blender: StubBlender | None = None,
    qa: StubQA | None = None,
    budget: BudgetTracker | None = None,
    max_revisions: int = 1,
) -> tuple[PipelineRunner, RunOutcome]:
    brief = Brief(text="Une ruelle sombre sous la pluie.")
    runner = PipelineRunner(
        project_id="proj-1",
        director=StubDirector(),
        blender=blender or StubBlender(),
        qa=qa or StubQA(),
        workdir=tmp_path,
        budget=budget,
        cost_hook=lambda step: {"director": 0.10, "blender": 0.20, "qa": 0.05}.get(step, 0.0),
        max_revisions=max_revisions,
    )
    outcome = await runner.run(brief)
    return runner, outcome


def _kinds(path: Path) -> list[str]:
    return [
        json.loads(line)["kind"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.asyncio
async def test_happy_path_produces_traced_run(tmp_path: Path) -> None:
    runner, outcome = await _run(tmp_path)

    assert outcome.run.status == "completed"
    assert outcome.revisions == 0
    assert outcome.scene is not None
    assert outcome.script is not None
    assert outcome.report is not None and outcome.report.passed

    for name in ("director", "blender", "qa", "render"):
        assert outcome.run.steps[name].status == "completed"

    kinds = _kinds(tmp_path / "events.jsonl")
    assert kinds[0] == "run_started"
    assert kinds[-1] == "run_completed"
    assert kinds.count("step_completed") == 4
    assert "cost_recorded" in kinds

    types = sorted(art.type for art in outcome.artifacts._artifacts.values())
    assert types == ["blender_script", "scene_spec"]
    script_art = next(
        a for a in outcome.artifacts._artifacts.values() if a.type == "blender_script"
    )
    assert script_art.status == "generated"
    assert script_art.cost == pytest.approx(0.20)

    spec_art = next(
        a for a in outcome.artifacts._artifacts.values() if a.type == "scene_spec"
    )
    assert outcome.provenance.parents(script_art.id) == [spec_art.id]


@pytest.mark.asyncio
async def test_invalid_script_blocks_and_targets_blender(tmp_path: Path) -> None:
    runner, outcome = await _run(tmp_path, blender=StubBlender([INVALID_SCRIPT]), max_revisions=2)

    assert outcome.run.status == "blocked"
    assert outcome.revisions == 2
    assert outcome.report is not None and not outcome.report.passed
    assert outcome.report.issues and outcome.report.issues[0].kind == IssueKind.TECHNICAL

    kinds = _kinds(tmp_path / "events.jsonl")
    assert kinds[-1] == "run_blocked"
    assert kinds.count("revision_requested") == 2
    assert "cost_recorded" in kinds

    revisions = [
        a for a in outcome.artifacts._artifacts.values() if a.type == "revision_spec"
    ]
    assert len(revisions) == 2
    payload = json.loads((tmp_path / "revision_1_blender.json").read_text(encoding="utf-8"))
    assert payload["target_step"] == "blender"
    assert payload["issues"][0]["kind"] == "technical"


@pytest.mark.asyncio
async def test_revision_recovers_and_completes(tmp_path: Path) -> None:
    blender = StubBlender([INVALID_SCRIPT, VALID_SCRIPT])
    runner, outcome = await _run(tmp_path, blender=blender, max_revisions=1)

    assert blender.calls == 2
    assert outcome.run.status == "completed"
    assert outcome.revisions == 1
    kinds = _kinds(tmp_path / "events.jsonl")
    assert kinds.count("revision_requested") == 1
    assert kinds[-1] == "run_completed"


@pytest.mark.asyncio
async def test_qa_failure_targets_director_when_issue_says_so(tmp_path: Path) -> None:
    class FailingQA(StubQA):
        async def assess(self, spec: SceneSpec, artifact_path: str, code: str = "") -> QAReport:
            return QAReport(
                passed=False,
                score=0.4,
                issues=[Issue(kind=IssueKind.SEMANTIC, message="brief non respecté", step="director")],
            )

    runner, outcome = await _run(tmp_path, qa=FailingQA(), max_revisions=1)

    assert outcome.run.status == "blocked"
    assert outcome.revisions == 1
    payload = json.loads((tmp_path / "revision_1_director.json").read_text(encoding="utf-8"))
    assert payload["target_step"] == "director"


@pytest.mark.asyncio
async def test_revision_injects_feedback_into_agent_context(tmp_path: Path) -> None:
    """La révision est « informée » : les issues QA atteignent le contexte NOOA
    de l'agent ciblé (``revision_feedback``) avant la régénération."""

    class RecordingContext:
        def __init__(self) -> None:
            self.static: dict[str, str] = {}

        def set_static(self, key: str, value: str) -> None:
            self.static[key] = value

    class ContextBlender(StubBlender):
        def __init__(self) -> None:
            super().__init__([VALID_SCRIPT, VALID_SCRIPT])
            self.context = RecordingContext()

    class FailingQA(StubQA):
        async def assess(self, spec: SceneSpec, artifact_path: str, code: str = "") -> QAReport:
            return QAReport(
                passed=False,
                score=0.3,
                issues=[Issue(kind=IssueKind.VISUAL, message="exposition surexposée", step="blender")],
                recommendations=["baisser l'intensité des lumières"],
            )

    blender = ContextBlender()
    runner, outcome = await _run(tmp_path, blender=blender, qa=FailingQA(), max_revisions=1)

    assert outcome.revisions == 1
    feedback = blender.context.static.get("revision_feedback", "")
    assert "Révision 1" in feedback
    assert "[visual]" in feedback
    assert "exposition surexposée" in feedback
    assert "baisser l'intensité des lumières" in feedback


@pytest.mark.asyncio
async def test_revision_spec_instructions_carry_formatted_issues(tmp_path: Path) -> None:
    """Le RevisionSpec persistant embarque les issues formatées (pas un texte générique)."""

    class FailingQA(StubQA):
        async def assess(self, spec: SceneSpec, artifact_path: str, code: str = "") -> QAReport:
            return QAReport(
                passed=False,
                score=0.2,
                issues=[Issue(kind=IssueKind.VISUAL, message="exposition surexposée", step="blender")],
            )

    _, outcome = await _run(tmp_path, qa=FailingQA(), max_revisions=1)

    payload = json.loads((tmp_path / "revision_1_blender.json").read_text(encoding="utf-8"))
    assert payload["target_step"] == "blender"
    assert "exposition surexposée" in payload["instructions"]
    assert "[visual]" in payload["instructions"]


@pytest.mark.asyncio
async def test_qa_receives_script_code_inline(tmp_path: Path) -> None:
    """Régression : l'agent QA (sandboxé) reçoit le code, pas un chemin hôte."""
    qa = StubQA()
    runner, outcome = await _run(tmp_path, qa=qa)

    assert outcome.run.status == "completed"
    assert qa.received_code == [VALID_SCRIPT]
    assert (tmp_path / "stub_scene" / "script.py").read_text(encoding="utf-8") == VALID_SCRIPT


@pytest.mark.asyncio
async def test_budget_records_agent_costs(tmp_path: Path) -> None:
    budget = BudgetTracker(budget=1.0, run_id="run-1")
    _, outcome = await _run(tmp_path, budget=budget)

    assert budget.llm == pytest.approx(0.35)
    assert not budget.over_budget()
    assert outcome.budget is budget


@pytest.mark.asyncio
async def test_budget_exhausted_blocks_before_execution(tmp_path: Path) -> None:
    """Enforcement déterministe du budget : aucun agent n'est appelé si dépassé."""
    budget = BudgetTracker(budget=0.0, run_id="run-1")
    budget.add_llm(1.0)
    assert budget.over_budget()

    runner, outcome = await _run(tmp_path, budget=budget)

    assert outcome.run.status == "blocked"
    assert outcome.revisions == 0
    assert outcome.scene is None
    assert outcome.script is None

    kinds = _kinds(tmp_path / "events.jsonl")
    assert kinds[0] == "run_started"
    assert kinds[-1] == "run_blocked"
    assert "director" not in [k for k in kinds if k.startswith("step_")]


@pytest.mark.asyncio
async def test_human_revision_injects_comment_into_target_agent(tmp_path: Path) -> None:
    """HITL : le commentaire du formulaire « Demander une révision » atteint
    l'agent ciblé comme ``revision_feedback`` au démarrage du run."""

    class RecordingContext:
        def __init__(self) -> None:
            self.static: dict[str, str] = {}

        def set_static(self, key: str, value: str) -> None:
            self.static[key] = value

    class ContextBlender(StubBlender):
        def __init__(self) -> None:
            super().__init__()
            self.context = RecordingContext()

    blender = ContextBlender()
    revision = {
        "type": "revision_request",
        "target_step": "blender",
        "comment": "Plus de pluie sur les réverbères.",
        "requested_by": "producer@example.com",
        "requested_at": "2026-08-11T00:00:00+00:00",
    }
    (tmp_path / "revision_request_123.json").write_text(json.dumps(revision), encoding="utf-8")

    runner, outcome = await _run(tmp_path, blender=blender)

    assert outcome.run.status == "completed"
    feedback = blender.context.static.get("revision_feedback", "")
    assert "Révision humaine" in feedback
    assert "Plus de pluie sur les réverbères." in feedback
    kinds = _kinds(tmp_path / "events.jsonl")
    assert "revision_applied" in kinds


@pytest.mark.asyncio
async def test_human_revision_consumed_after_terminal_run(tmp_path: Path) -> None:
    """Un run completed/blocked consomme la demande (renommée .applied) pour
    qu'un « Relancer le run » ultérieur ne ré-applique pas l'ancien commentaire."""
    revision = {
        "type": "revision_request",
        "target_step": "blender",
        "comment": "Ajouter du brouillard.",
    }
    (tmp_path / "revision_request_123.json").write_text(json.dumps(revision), encoding="utf-8")

    _, outcome = await _run(tmp_path)

    assert outcome.run.status == "completed"
    assert [p for p in tmp_path.glob("revision_request_*.json") if ".applied" not in p.name] == []
    assert (tmp_path / "revision_request_123.applied.json").is_file()


@pytest.mark.asyncio
async def test_human_revision_not_consumed_on_exception(tmp_path: Path) -> None:
    """Un run interrompu par une exception conserve la demande : un retry
    (« Relancer le run ») ré-applique le même commentaire."""

    class ExplodingDirector(StubDirector):
        async def plan_scene(self, brief: Brief) -> SceneSpec:
            raise RuntimeError("panne LLM transitoire")

    revision = {
        "type": "revision_request",
        "target_step": "blender",
        "comment": "Ne pas toucher à cette demande.",
    }
    (tmp_path / "revision_request_123.json").write_text(json.dumps(revision), encoding="utf-8")

    runner = PipelineRunner(
        project_id="proj-1",
        director=ExplodingDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
    )
    with pytest.raises(RuntimeError):
        await runner.run(Brief(text="Une ruelle sombre sous la pluie."))

    assert (tmp_path / "revision_request_123.json").is_file()


@pytest.mark.asyncio
async def test_human_revision_targets_director_when_asked(tmp_path: Path) -> None:
    """Le commentaire cible l'agent demandé (ici director)."""

    class RecordingContext:
        def __init__(self) -> None:
            self.static: dict[str, str] = {}

        def set_static(self, key: str, value: str) -> None:
            self.static[key] = value

    class ContextDirector(StubDirector):
        def __init__(self) -> None:
            self.context = RecordingContext()

        async def plan_scene(self, brief: Brief) -> SceneSpec:
            return SceneSpec(brief=brief.text)

    revision = {
        "type": "revision_request",
        "target_step": "director",
        "comment": "Plus sombre, caméra plus basse.",
    }
    (tmp_path / "revision_request_123.json").write_text(json.dumps(revision), encoding="utf-8")

    director = ContextDirector()
    runner = PipelineRunner(
        project_id="proj-1",
        director=director,
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
    )
    outcome = await runner.run(Brief(text="Une ruelle sombre sous la pluie."))

    assert outcome.run.status == "completed"
    feedback = director.context.static.get("revision_feedback", "")
    assert "Plus sombre, caméra plus basse." in feedback


@pytest.mark.asyncio
async def test_run_history_injected_into_agent_context(tmp_path: Path) -> None:
    """Les agents reçoivent l'historique récent du run (``run_history``)."""

    class RecordingContext:
        def __init__(self) -> None:
            self.static: dict[str, str] = {}

        def set_static(self, key: str, value: str) -> None:
            self.static[key] = value

    class ContextBlender(StubBlender):
        def __init__(self) -> None:
            super().__init__()
            self.context = RecordingContext()

    blender = ContextBlender()
    _, outcome = await _run(tmp_path, blender=blender)

    assert outcome.run.status == "completed"
    history = blender.context.static.get("run_history", "")
    assert "step_completed" in history
    assert "cost_recorded" in history