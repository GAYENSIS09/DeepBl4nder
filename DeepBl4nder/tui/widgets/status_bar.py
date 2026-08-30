"""Status bar widget - run state, current step, model, live cost and budget."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


def _clock() -> str:
    return datetime.now().strftime("%H:%M:%S")


class StatusBar(Widget):
    """Bottom bar tracking the active run's budget, step and provider."""

    _status: reactive[str] = reactive("idle")
    _step: reactive[str] = reactive("no run")
    _cost: reactive[float] = reactive(0.0)
    _budget: reactive[float] = reactive(0.0)
    _models: reactive[str] = reactive("-")

    def __init__(self, *, id: str = "status-bar") -> None:
        super().__init__(id=id)

    def compose(self) -> ComposeResult:
        with Horizontal(id="status-row"):
            yield Label("idle", id="status-text", classes="status-idle")
            yield Label("|", classes="status-sep")
            yield Label("step", id="step-text", classes="step-idle")
            yield Label("|", classes="status-sep")
            yield Label("models: -", id="models-text", classes="models-idle")
            yield Label("|", classes="status-sep")
            yield Label("cost $0.00", id="cost-text", classes="cost-idle")
            yield Label("|", classes="status-sep")
            yield Label("budget $1.00", id="budget-text", classes="budget-idle")
            yield Label("", id="clock-text", classes="clock")
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self.query_one("#clock-text", Label).update(_clock())

    def watch__status(self, value: str) -> None:
        self.query_one("#status-text", Label).update(value)
        self.query_one("#status-text", Label).set_classes(f"status-{value.replace(' ', '-')}")

    def watch__step(self, value: str) -> None:
        self.query_one("#step-text", Label).update(f"step: {value}")

    def watch__cost(self, value: float) -> None:
        self.query_one("#cost-text", Label).update(f"cost ${value:.2f}")

    def watch__budget(self, value: float) -> None:
        remaining = max(0.0, value - self._cost)
        label = self.query_one("#budget-text", Label)
        label.update(f"budget ${value:.2f} - ${remaining:.2f} left")
        label.set_classes("budget-warning" if remaining <= value * 0.2 else "budget-idle")

    def watch__models(self, value: str) -> None:
        self.query_one("#models-text", Label).update(f"models: {value}")

    def on_mount(self) -> None:
        self._tick()

    def set_running(self, running: bool) -> None:
        self._status = "running" if running else "idle"

    def set_step(self, step: str) -> None:
        self._step = step or "no run"

    def set_cost(self, cost: float) -> None:
        self._cost = cost

    def set_budget(self, budget: float) -> None:
        self._budget = budget

    def set_provider(self, models: str) -> None:
        self._models = models or "-"
