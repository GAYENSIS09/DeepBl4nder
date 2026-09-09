"""Tests du pont d'événements TUI (event_bridge.py) : normalization de la
surface NOOA en événements du flux. Utilise un agent + event manager stub pour
isoler le bridge de NOOA.

Couvre notamment l'observabilité ajoutée : messages transactionnels
déterminés et l'ensemble des types d'événements émis par le bridge.
"""

from __future__ import annotations

from types import SimpleNamespace

from DeepBl4nder.tui.event_bridge import EventBroker, attach_agent_bridge


class FakeEventManager:
    """Mini event_manager NOOA : enregistre et relâche les handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, callable] = {}

    def on(self, event_type: str, handler: callable) -> None:
        self._handlers[event_type] = handler

    def fire(self, event_type: str, event: object) -> None:
        handler = self._handlers.get(event_type)
        if handler is not None:
            handler(event)


class FakeAgent:
    """Mini agent : expose event_manager + _get_last_call_info."""

    def __init__(self) -> None:
        self.event_manager = FakeEventManager()
        self._llm = None

    def _get_last_call_info(self) -> dict:
        return {}


def _make_bridge(actor: str = "director", production_id: str = "p1"):
    agent = FakeAgent()
    broker = EventBroker(history_size=100)
    attach_agent_bridge(
        agent=agent,
        actor=actor,
        broker=broker,
        production_id=lambda: production_id,
    )
    return agent, broker


def test_bridge_exposes_agent_harness_lifecycle() -> None:
    agent, broker = _make_bridge()
    agent.event_manager.fire(
        "BeforeAgentCall",
        SimpleNamespace(
            method_name="design_scene",
            needs_generation=True,
            is_top_level=True,
            call_id="call-abc123",
            parent_call_id=None,
        ),
    )
    agent.event_manager.fire(
        "AfterAgentCall",
        SimpleNamespace(
            method_name="design_scene",
            needs_generation=True,
            is_top_level=True,
            call_id="call-abc123",
            parent_call_id=None,
            success=True,
            exception_type=None,
        ),
    )
    events = broker.history()
    kinds = [e.kind for e in events]
    assert "agent_call_start" in kinds
    assert "agent_call_end" in kinds
    start = next(e for e in events if e.kind == "agent_call_start")
    assert start.actor == "director"
    assert "design_scene" in start.content
    assert "LLM method" in start.content
    assert start.meta["call_id"] == "call-abc123"
    end = next(e for e in events if e.kind == "agent_call_end")
    assert "done" in end.content
    assert end.meta["success"] is True


def test_bridge_reports_nested_python_method() -> None:
    agent, broker = _make_bridge(actor="blender")
    agent.event_manager.fire(
        "BeforeAgentCall",
        SimpleNamespace(
            method_name="_helpers",
            needs_generation=False,
            is_top_level=False,
            call_id="call-x",
            parent_call_id="call-abc123",
        ),
    )
    events = broker.history()
    start = next(e for e in events if e.kind == "agent_call_start")
    assert "python method" in start.content
    assert "(nested)" in start.content
    assert start.meta["needs_generation"] is False
    assert start.meta["parent_call_id"] == "call-abc123"


def test_bridge_reports_context_compaction_summary() -> None:
    agent, broker = _make_bridge()
    agent.event_manager.fire(
        "Summary",
        SimpleNamespace(
            replaced_range=(1, 22),
            summary_text="User discussed the rain-soaked alley and camera angles.",
        ),
    )
    events = broker.history()
    compacted = next(e for e in events if e.kind == "context_compacted")
    assert "1..22" in compacted.content
    assert "summarized" in compacted.content
    assert compacted.meta["summary_text"].startswith("User discussed")


def test_bridge_reports_pure_truncation_without_summary() -> None:
    agent, broker = _make_bridge()
    agent.event_manager.fire("Summary", SimpleNamespace(replaced_range=(2, 40), summary_text=None))
    events = broker.history()
    compacted = next(e for e in events if e.kind == "context_compacted")
    assert compacted.content.startswith("context collapsed:")
    assert compacted.meta["collapsed"] is True


def test_bridge_reports_python_tool_result_value() -> None:
    agent, broker = _make_bridge(actor="blender")
    agent.event_manager.fire(
        "PythonOutput",
        SimpleNamespace(stdout="", stderr="", error="", value={"shots": 3}),
    )
    events = broker.history()
    result = next(e for e in events if e.kind == "tool_result")
    assert "shots" in result.content
    assert result.meta["_full"] == "{'shots': 3}"


def test_bridge_tolerates_unknown_event_types() -> None:
    agent, broker = _make_bridge()
    # Un type inconnu ne doit ni lever ni produire d'événement.
    agent.event_manager.fire("MadeUpEvent", SimpleNamespace(anything=1))
    assert broker.history() == []