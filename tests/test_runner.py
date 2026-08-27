"""Tests d'intégration : PipelineRunner (brief -> Director -> Blender -> QA)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from deepblender.domain.project import Brief
from deepblender.domain.qa import QAReport, Issue, IssueKind
from deepblender.domain.scene import BlenderScript, SceneSpec
from deepblender.domain.media import LanguagePackage
from deepblender.production.budget import BudgetTracker
from deepblender.production.runner import PipelineRunner, RunOutcome
from nooa.errors import GenerationError

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


def _events(path: Path) -> list[dict]:
    return [
        json.loads(line)
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
# ------------------------------------------------------- reprise (checkpoints)


class CountingDirector(StubDirector):
    """StubDirector qui compte ses appels (pour vérifier la reprise)."""

    def __init__(self) -> None:
        self.calls = 0

    async def plan_scene(self, brief: Brief) -> SceneSpec:
        self.calls += 1
        return await super().plan_scene(brief)


class CountingQA(StubQA):
    """StubQA qui compte ses appels."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def assess(self, spec: SceneSpec, artifact_path: str, code: str = "") -> QAReport:
        self.calls += 1
        return await super().assess(spec, artifact_path, code=code)


@pytest.mark.asyncio
async def test_completed_run_resumes_without_recalling_agents(tmp_path: Path) -> None:
    brief = Brief(text="Une ruelle sombre sous la pluie battante.")
    first = PipelineRunner(
        project_id="proj-resume",
        director=StubDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
    )
    outcome1 = await first.run(brief)
    assert outcome1.run.status == "completed"

    state = json.loads((tmp_path / "run_state.json").read_text(encoding="utf-8"))
    assert state["brief_sha256"]
    assert set(state["steps"]) >= {"director", "blender", "qa"}

    director, qa = CountingDirector(), CountingQA()
    second = PipelineRunner(
        project_id="proj-resume",
        director=director,
        blender=StubBlender(),
        qa=qa,
        workdir=tmp_path,
    )
    outcome2 = await second.run(brief)

    assert outcome2.run.status == "completed"
    assert director.calls == 0
    assert qa.calls == 0
    assert outcome2.scene is not None
    assert outcome2.report is not None and outcome2.report.passed
    kinds = _kinds(tmp_path / "events.jsonl")
    assert kinds.count("step_resumed") >= 3  # director + blender + qa
    assert kinds.count("resume_ready") == 1


@pytest.mark.asyncio
async def test_brief_change_invalidates_checkpoints(tmp_path: Path) -> None:
    first = PipelineRunner(
        project_id="proj-brief",
        director=StubDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
    )
    await first.run(Brief(text="Brief original."))

    director, qa = CountingDirector(), CountingQA()
    second = PipelineRunner(
        project_id="proj-brief",
        director=director,
        blender=StubBlender(),
        qa=qa,
        workdir=tmp_path,
    )
    outcome = await second.run(Brief(text="Un brief completement different."))
    assert outcome.run.status == "completed"
    assert director.calls == 1
    assert qa.calls == 1
    assert "step_resumed" not in _kinds(tmp_path / "events.jsonl")


@pytest.mark.asyncio
async def test_revision_request_targets_blender_and_reuses_upstream(tmp_path: Path) -> None:
    first = PipelineRunner(
        project_id="proj-rev",
        director=StubDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
    )
    await first.run(Brief(text="Cible revision."))

    (tmp_path / "revision_request_001.json").write_text(
        json.dumps({"target_step": "blender", "feedback": "Rends la nuit plus sombre"}),
        encoding="utf-8",
    )
    director, qa = CountingDirector(), CountingQA()
    second = PipelineRunner(
        project_id="proj-rev",
        director=director,
        blender=StubBlender(),
        qa=qa,
        workdir=tmp_path,
    )
    outcome = await second.run(Brief(text="Cible revision."))
    assert outcome.run.status == "completed"
    assert director.calls == 0  # amont repris depuis les checkpoints
    assert qa.calls == 1  # blender + qa rejoues
    resumed_steps = [
        e.get("payload", {}).get("step")
        for e in _events(tmp_path / "events.jsonl")
        if e.get("kind") == "step_resumed"
    ]
    assert "director" in resumed_steps


@pytest.mark.asyncio
async def test_corrupted_checkpoint_falls_back_to_full_rerun(tmp_path: Path) -> None:
    first = PipelineRunner(
        project_id="proj-corrupt",
        director=StubDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
    )
    await first.run(Brief(text="Checkpoint corrompu."))

    (tmp_path / "scene_spec.json").write_text("{invalid json", encoding="utf-8")
    director, qa = CountingDirector(), CountingQA()
    second = PipelineRunner(
        project_id="proj-corrupt",
        director=director,
        blender=StubBlender(),
        qa=qa,
        workdir=tmp_path,
    )
    outcome = await second.run(Brief(text="Checkpoint corrompu."))
    assert outcome.run.status == "completed"
    assert director.calls == 1  # chaine cassee : on rejoue a partir du directeur
    assert qa.calls == 1


class ConcurrencyTrackingLocalization:
    """Stub LocalizationAgent qui mesure la concurrence effective."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    def default_languages(self) -> list[str]:
        return []

    async def plan_localization(self, scene: SceneSpec, lang: str, languages=None):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.05)
        self.active -= 1
        return LanguagePackage(language=lang, languages=list(languages or [lang]))


@pytest.mark.asyncio
async def test_localization_languages_produced_in_parallel(tmp_path: Path) -> None:
    loc = ConcurrencyTrackingLocalization()
    runner = PipelineRunner(
        project_id="proj-loc",
        director=StubDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
        localization=loc,
        target_languages=["fr", "en", "wo", "ar"],
    )
    runner._llm_semaphore = asyncio.Semaphore(4)
    scene = SceneSpec(brief="parallelisation")

    packages = await runner.postprod.run_localization(scene)

    assert [p.language for p in packages] == ["fr", "en", "wo", "ar"]  # ordre preserve
    assert loc.max_active >= 2  # les langues se chevauchent reellement


class FlakyDirector:
    """Directeur qui échoue N fois avec GenerationError avant de réussir."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def plan_scene(self, brief: Brief) -> SceneSpec:
        self.calls += 1
        if self.calls <= self.failures:
            raise GenerationError(
                "return_result validation failed after 3 attempts.\n"
                "Last error:\nMethod invariant failed: shots non vide."
            )
        return SceneSpec(brief=brief.text)


def _retry_runner(tmp_path: Path, director: FlakyDirector) -> PipelineRunner:
    return PipelineRunner(
        project_id="proj-retry",
        director=director,
        blender=StubBlender(),
        qa=StubQA(),
        workdir=tmp_path,
    )


@pytest.mark.asyncio
async def test_generation_error_retries_with_fresh_generation(tmp_path: Path) -> None:
    """Régression du log 20:38 : un modèle de secours qui s'enlise sur la
    validation ne doit pas tuer le run — une génération fraîche est tentée."""
    director = FlakyDirector(failures=1)
    runner = _retry_runner(tmp_path, director)

    outcome = await runner.run(Brief(text="test retry"))

    assert director.calls == 2  # 1er essai KO + génération fraîche OK
    kinds = [e.kind for e in runner.event_log.load()]
    assert "llm_retry" in kinds
    assert outcome is not None


@pytest.mark.asyncio
async def test_generation_error_twice_still_propagates(tmp_path: Path) -> None:
    """Deux générations infructueuses : l'erreur remonte (pas de boucle infinie)."""
    director = FlakyDirector(failures=99)
    runner = _retry_runner(tmp_path, director)

    with pytest.raises(GenerationError):
        await runner.run(Brief(text="test échec définitif"))

    assert director.calls == 2


class AlwaysFailingStoryboard:
    async def plan_storyboard(self, story_spec):
        raise GenerationError(
            "return_result validation failed after 3 attempts.\n"
            "Last error:\nMethod invariant failed: shots non vide."
        )


class FixedStory:
    def __init__(self, spec) -> None:
        self.spec = spec

    async def plan_story(self, brief: Brief):
        return self.spec


def _story_with_beats() -> "StorySpec":
    from deepblender.domain.narrative import Act, StoryBeat, StorySpec

    return StorySpec(
        logline="Une nuit décisive.",
        synopsis="Une hackeuse remonte la piste de ses souvenirs vendus.",
        acts=[
            Act(
                name="I",
                order=0,
                beats=[
                    StoryBeat(description="ouverture : intrusion dans le serveur", duration_estimate=4.0),
                    StoryBeat(description="retournement : le frère apparaît", duration_estimate=6.0),
                ],
            )
        ],
    )


@pytest.mark.asyncio
async def test_storyboard_synthesized_from_beats_when_model_fails_twice(tmp_path: Path) -> None:
    """Régression du log 21:51 : shots vides malgré retry → storyboard
    déterministe depuis les beats au lieu d'un run tué."""
    runner = PipelineRunner(
        project_id="proj-synth",
        director=StubDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        story=FixedStory(_story_with_beats()),
        storyboard=AlwaysFailingStoryboard(),
        workdir=tmp_path,
    )
    outcome = await runner.run(Brief(text="test synthèse"))

    assert outcome is not None
    path = tmp_path / "storyboard_spec.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["shots"]) == 2
    assert data["shots"][0]["description"].startswith("ouverture")
    assert data["shots"][1]["camera_angle"] == "medium"  # cycle wide→medium
    assert abs(data["total_duration"] - 10.0) < 1e-9
    kinds = [e.kind for e in runner.event_log.load()]
    assert "storyboard_synthesized" in kinds


@pytest.mark.asyncio
async def test_storyboard_synthesis_fallback_when_story_empty(tmp_path: Path) -> None:
    """Histoire elle-même vide : un plan d'exposition unique, run survit."""
    from deepblender.domain.narrative import StorySpec

    empty_story = StorySpec(logline="", synopsis="")
    runner = PipelineRunner(
        project_id="proj-synth2",
        director=StubDirector(),
        blender=StubBlender(),
        qa=StubQA(),
        story=FixedStory(empty_story),
        storyboard=AlwaysFailingStoryboard(),
        workdir=tmp_path,
    )
    await runner.run(Brief(text="test dégradé"))

    data = json.loads((tmp_path / "storyboard_spec.json").read_text(encoding="utf-8"))
    assert len(data["shots"]) == 1
    assert data["shots"][0]["description"]


class AlwaysFailingBlender:
    """Régression du log 22:49 : le modèle recopie l'enveloppe d'appel
    au lieu du résultat → GenerationError après 3 essais, deux fois."""

    def __init__(self) -> None:
        self.calls = 0

    async def build_script(self, spec: SceneSpec) -> BlenderScript:
        self.calls += 1
        raise GenerationError(
            "return_result validation failed after 3 attempts.\n"
            "Last error:\n'result' has wrong type. Expected: BlenderScript, Got: str"
        )


@pytest.mark.asyncio
async def test_blender_script_synthesized_when_model_fails_twice(tmp_path: Path) -> None:
    """Deux générations blender infructueuses : script bpy déterministe
    depuis la SceneSpec au lieu de tuer le run après ~8 minutes."""
    blender = AlwaysFailingBlender()
    runner = PipelineRunner(
        project_id="proj-blender-synth",
        director=StubDirector(),
        blender=blender,
        qa=StubQA(),
        workdir=tmp_path,
    )
    outcome = await runner.run(Brief(text="Une ruelle néon sous la pluie."))

    assert blender.calls == 2  # génération initiale + retry
    assert outcome.run.status == "completed"
    assert outcome.script is not None
    assert outcome.script.scene_name.startswith("scene_synthetisee_")
    assert "import bpy" in outcome.script.code
    # Le script doit RENDRE réellement (log 00:45 : sans appel de rendu,
    # « No media file produced by Blender script ») :
    assert "bpy.ops.render.render(animation=True)" in outcome.script.code
    # …vers une sortie ABSOLUE dans le dossier scanné par l'étape render :
    assert "scene.render.filepath = r'" in outcome.script.code
    assert "//render_synthetisee_" not in outcome.script.code
    render_dir = tmp_path / "render"
    assert render_dir.is_dir()
    embedded_prefix = next(
        line for line in outcome.script.code.splitlines()
        if line.startswith("scene.render.filepath")
    )
    assert str(render_dir.resolve()).replace("\\", "/") in embedded_prefix.replace("\\", "/")
    # Le script est bien écrit sur disque pour l'étape rendu :
    script_files = list(tmp_path.glob("*/script.py"))
    assert len(script_files) == 1
    assert "bpy" in script_files[0].read_text(encoding="utf-8")

    kinds = [e.kind for e in runner.event_log.load()]
    assert "blender_script_synthesized" in kinds
    assert "llm_retry" in kinds
