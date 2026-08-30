"""Main TUI application for DeepBl4nder - embedded mode (no HTTP, no auth).

Open a real-time console: type a brief, watch the NOOA agents reason, produce
and render, and inspect the artifacts left in the library. The app wires the
real agent crew itself (``EmbeddedAPI.create_agents``): there is no fake mode,
so a missing LLM provider surfaces as a readable error instead of a broken run.
"""

from __future__ import annotations

import os
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.theme import Theme
from textual.widgets import Footer, Header

from DeepBl4nder.tui import theme
from DeepBl4nder.tui.embedded_api import EmbeddedAPI, get_embedded_api


def _brand_theme() -> Theme:
    return Theme(
        name="deepbl4nder",
        primary=theme.ACCENT,
        secondary=theme.ACCENT_2,
        accent=theme.ACCENT,
        success=theme.SUCCESS,
        warning=theme.WARNING,
        error=theme.ERROR,
        foreground=theme.TEXT,
        background=theme.BACKGROUND,
        surface=theme.SURFACE,
        panel=theme.PANEL,
        dark=True,
        variables={
            "text": theme.TEXT,
            "text-muted": theme.TEXT_MUTED,
            "text-dim": theme.TEXT_DIM,
        },
    )


class DeepBl4nderTUI(App):
    """DeepBl4nder Textual TUI - AI-powered audiovisual production in a console."""

    TITLE = "DeepBl4nder"
    SUB_TITLE = "NOOA Agent Orchestration"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+b", "artifacts", "Artifacts", show=True),
        Binding("ctrl+o", "settings", "Settings", show=True),
        Binding("f1", "help", "Help", show=True),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.register_theme(_brand_theme())
        self.theme = "deepbl4nder"
        self._embedded_api: EmbeddedAPI | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    async def on_mount(self) -> None:
        data_dir = os.environ.get("DeepBl4nder_DATA_DIR", "data")
        self._embedded_api = get_embedded_api(data_dir=data_dir)
        self.install_screen(self.console_screen, name="console")
        self.install_screen(self.library_screen, name="library")
        self.install_screen(self.settings_screen, name="settings")
        self.push_screen("console")

    # ========== Screens ==========

    @property
    def console_screen(self):
        from DeepBl4nder.tui.screens.console import ConsoleScreen

        return ConsoleScreen(self.api)

    @property
    def library_screen(self):
        from DeepBl4nder.tui.screens.library import LibraryScreen

        return LibraryScreen(self.api)

    @property
    def settings_screen(self):
        from DeepBl4nder.tui.screens.settings_modal import SettingsModal

        return SettingsModal(self.api)

    @property
    def api(self) -> EmbeddedAPI:
        assert self._embedded_api is not None
        return self._embedded_api

    # ========== Actions ==========

    def action_artifacts(self) -> None:
        """Toggle the artifact library on top of the console."""
        if self.screen.name == "library":
            self.pop_screen()
            return
        self.push_screen("library")

    def action_settings(self) -> None:
        """Open the settings modal."""
        self.push_screen("settings")

    def action_help(self) -> None:
        header = "[b]DeepBl4nder[/b] - opencode-style console for AI film production"

        def make_text(keys: str, desc: str) -> str:
            return f"[b]{keys}[/b]  {desc}"

        self.notify(
            "\n".join(
                [
                    header,
                    make_text("ctrl+b", "Artifact library"),
                    make_text("ctrl+o", "Settings"),
                    make_text("ctrl+q", "Quit"),
                    make_text("enter/ctrl+enter", "Run the brief (Run button)"),
                ]
            ),
            title="Keyboard shortcuts",
            timeout=6,
        )

    async def on_unmount(self) -> None:
        if self._embedded_api is not None and self._embedded_api._run_task:
            self._embedded_api._run_task.cancel()