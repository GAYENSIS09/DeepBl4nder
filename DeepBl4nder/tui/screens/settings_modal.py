"""Settings modal - edits local pipeline configuration in memory."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Switch

from DeepBl4nder.tui.embedded_api import EmbeddedAPI


class SettingsModal(Screen):
    """Overlay screen with the editing progress row, persisted to the API."""

    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
    ]

    def __init__(self, api: EmbeddedAPI, *, name: str = "settings") -> None:
        super().__init__(name=name)
        self.api = api

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-backdrop"):
            with Container(id="settings-card"):
                yield Label("Settings", id="settings-title")
                yield Label("Local pipeline configuration", id="settings-subtitle")
                with Vertical(id="settings-fields"):
                    yield Horizontal(Label("Data directory", classes="setting-label"), Input(str(self.api.data_dir), id="set-data-dir", classes="setting-input"))
                    yield Horizontal(Label("Render budget (USD)", classes="setting-label"), Input(str(self.api.budget.budget), type="number", id="set-budget", classes="setting-input"))
                    yield Horizontal(Label("Max revisions", classes="setting-label"), Input(str(self.api.max_revisions), type="number", id="set-revisions", classes="setting-input"))
                    yield Horizontal(Label("Blender executable", classes="setting-label"), Input(self._bridge_exe(), id="set-blender", classes="setting-input", placeholder="auto-detected"))
                    yield Horizontal(Label("Enable generation cache", classes="setting-label"), Switch(value=self.api.enable_cache, id="set-cache", classes="setting-input"))
                with Horizontal(id="settings-actions"):
                    yield Button("Save", id="btn-settings-save", variant="success")
                    yield Button("Close", id="btn-settings-close", variant="default")

    def _bridge_exe(self) -> str:
        bridge = self.api.blender_bridge
        exe = getattr(bridge, "_blender_exe", None)
        return exe if isinstance(exe, str) else ""

    def _save(self) -> None:
        try:
            data_dir = self.query_one("#set-data-dir", Input).value.strip()
            if data_dir:
                self.api.data_dir = data_dir
            budget = float(self.query_one("#set-budget", Input).value)
            if budget > 0:
                self.api.budget.budget = budget
            revisions = int(self.query_one("#set-revisions", Input).value)
            if revisions >= 0:
                self.api.max_revisions = revisions
            blender = self.query_one("#set-blender", Input).value.strip()
            if blender:
                self.api.blender_bridge._blender_exe = blender
            else:
                from DeepBl4nder.bridges.blender.bridge import _find_blender

                self.api.blender_bridge._blender_exe = _find_blender()
            self.api.enable_cache = self.query_one("#set-cache", Switch).value
            self.notify("Settings saved", severity="success")
        except ValueError as exc:
            self.notify(f"Invalid value: {exc}", severity="error")
            return
        self.app.pop_screen()

    def action_save(self) -> None:
        self._save()

    def action_close(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-settings-save")
    def _on_save(self) -> None:
        self.action_save()

    @on(Button.Pressed, "#btn-settings-close")
    def _on_close(self) -> None:
        self.action_close()