"""Production : runs, étapes, événements, reprise et budget."""

from __future__ import annotations

import pytest

from DeepBl4nder.production.budget import BudgetAlert, BudgetTracker
from DeepBl4nder.production.events import EventLog
from DeepBl4nder.production.runs import ProductionRun, ProductionStep


def _status(run: ProductionRun, name: str) -> str:
    step = run.step(name)
    assert step is not None
    return step.status


def test_run_snapshot_and_pending_steps() -> None:
    run = ProductionRun(project_id="proj-1")
    run.add_step(ProductionStep(name="brief"))
    run.add_step(ProductionStep(name="render"))
    run.mark_step("brief", "completed")
    assert run.pending_steps() == ["render"]
    snapshot = run.snapshot()
    assert snapshot["status"] == "created"
    assert snapshot["steps"] == {"brief": "completed", "render": "pending"}


def test_correlation_ids() -> None:
    run = ProductionRun(project_id="proj-2")
    run.correlation["agent_run_id"] = "agent-1"
    run.correlation["event_id"] = "evt-9"
    assert run.correlation["agent_run_id"] == "agent-1"


def test_budget_within_budget() -> None:
    tracker = BudgetTracker(budget=1.0)
    tracker.add_llm(0.18)
    tracker.add_render(0.46)
    tracker.add_storage(0.02)
    assert tracker.total == 0.66
    assert tracker.remaining == pytest.approx(0.34)
    assert not tracker.over_budget()


def test_budget_alert_on_overflow() -> None:
    tracker = BudgetTracker(budget=1.0)
    tracker.add_llm(0.40)
    tracker.add_render(0.50)
    tracker.add_external(0.20)
    assert tracker.over_budget()


def test_budget_report() -> None:
    tracker = BudgetTracker(budget=1.0)
    tracker.add_llm(0.25)
    report = tracker.report()
    assert report["llm"] == 0.25
    assert report["total"] == 0.25
    assert report["budget"] == 1.0
    assert report["remaining"] == 0.75


def test_budget_alert_fires_once_on_overflow() -> None:
    tracker = BudgetTracker(budget=1.0)
    alerts: list[BudgetAlert] = []
    tracker.subscribe(alerts.append)
    tracker.add_llm(0.40)
    assert alerts == []
    tracker.add_render(0.70)
    assert len(alerts) == 1
    assert alerts[0].overshoot == pytest.approx(0.1)
    tracker.add_storage(0.10)
    assert len(alerts) == 1


def test_event_log_append_and_load(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    log.append("step_started", {"step": "brief"})
    log.append("step_completed", {"step": "brief"})
    events = log.load()
    assert [event.seq for event in events] == [1, 2]
    assert [event.kind for event in events] == ["step_started", "step_completed"]
    assert log.last_seq() == 2


def test_event_log_skips_corrupt_lines(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"seq": 1, "kind": "run_started", "ts": 0.0, "payload": {}}\nnot-json\n')
    assert len(EventLog(path).load()) == 1


def test_run_step_transitions_are_persisted(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    run = ProductionRun(project_id="p", log=log)
    run.add_step(ProductionStep(name="brief"))
    run.start_step("brief")
    run.complete_step("brief")
    assert [event.kind for event in log.load()] == ["step_started", "step_completed"]


def test_recovery_resumes_unconsumed_steps(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    log.append("run_started", {})
    log.append("step_started", {"step": "brief"})
    log.append("step_completed", {"step": "brief"})
    log.append("step_started", {"step": "render"})
    run = ProductionRun.recover("proj-9", log)
    assert run.status == "running"
    assert _status(run, "brief") == "completed"
    assert run.pending_steps() == ["render"]


def test_recovery_keeps_failed_steps(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    log.append("step_started", {"step": "qa"})
    log.append("step_failed", {"step": "qa"})
    run = ProductionRun.recover("proj-10", log)
    assert _status(run, "qa") == "failed"
    assert run.pending_steps() == []


def test_approval_workflow(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    run = ProductionRun(project_id="p", log=log)
    run.add_step(ProductionStep(name="previs"))
    run.request_approval("previs")
    assert run.status == "awaiting_approval"
    assert _status(run, "previs") == "awaiting_approval"
    run.approve("previs")
    assert run.status == "running"
    assert _status(run, "previs") == "approved"


def test_reject_sets_revision(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    run = ProductionRun(project_id="p", log=log)
    run.add_step(ProductionStep(name="story"))
    run.request_approval("story")
    run.reject("story", "refaire l'arc narratif")
    assert run.status == "revision"
    assert _status(run, "story") == "rejected"


def test_recovery_restores_pending_approval(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    log.append("run_started", {})
    log.append("approval_requested", {"step": "previs"})
    run = ProductionRun.recover("proj-11", log)
    assert run.status == "awaiting_approval"
    assert _status(run, "previs") == "awaiting_approval"


def test_recovery_approval_granted(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    log.append("approval_requested", {"step": "previs"})
    log.append("approval_granted", {"step": "previs"})
    run = ProductionRun.recover("proj-12", log)
    assert run.status == "running"
    assert _status(run, "previs") == "approved"
