"""Top input bar: brief text, target engine, run/cancel/copy actions."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, TextArea

ENGINE_OPTIONS = [
    ("Blender", "blender"),
    ("Unreal Engine 5", "ue5"),
    ("Godot", "godot"),
    ("AI Video", "ai_video"),
]


class TaskBar(Widget):
    """Composes the creative brief input with the engine picker and run controls."""

    def __init__(self, *, engine: str = "blender", id: str = "task-bar") -> None:
        super().__init__(id=id)
        self._engine = engine

    def compose(self) -> ComposeResult:
        with Vertical(id="taskbar-layout"):
            yield TextArea(
                "",
                id="brief-input",
                classes="brief-input",
                placeholder="Describe your film idea... e.g. a 30 second sci-fi short about a stranded rover",
            )
            with Horizontal(id="taskbar-controls"):
                with Horizontal(id="engine-row"):
                    yield Label("Engine", id="engine-label")
                    with Horizontal(id="engine-buttons"):
                        for label, value in ENGINE_OPTIONS:
                            selected = value == self._engine
                            yield Button(
                                label, id=f"engine-{value}",
                                classes=("engine-btn selected" if selected else "engine-btn"),
                            )
                with Horizontal(id="action-row"):
                    yield Button("Run", id="btn-run", variant="success")
                    yield Button("Cancel", id="btn-cancel", variant="error", disabled=True)
                    yield Button("Copy log", id="btn-copy", variant="default")

    @on(Button.Pressed, ".engine-btn")
    def _on_engine_pressed(self, event: Button.Pressed) -> None:
        self.set_engine(event.button.id.removeprefix("engine-"))

    def set_engine(self, value: str) -> None:
        self._engine = value
        for button in self.query(".engine-btn"):
            button.set_class(button.id == f"engine-{value}", "selected")

    @property
    def brief(self) -> str:
        return self.query_one("#brief-input", TextArea).text.strip()

    @property
    def engine(self) -> str:
        return self._engine

    def set_running(self, running: bool) -> None:
        self.query_one("#btn-run", Button).disabled = running
        self.query_one("#btn-cancel", Button).disabled = not running
        self.query_one("#brief-input", TextArea).disabled = running
