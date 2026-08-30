"""Base screen class for DeepBl4nder TUI (embedded mode)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.notifications import SeverityLevel
from textual.screen import Screen

from DeepBl4nder.tui.embedded_api import EmbeddedAPI

if TYPE_CHECKING:
    from DeepBl4nder.tui.app import DeepBl4nderTUI


class BaseScreen(Screen):
    """Base screen with common functionality."""

    def __init__(self, api: EmbeddedAPI, *, name: str | None = None):
        super().__init__(name=name)
        self.api = api
        self.app_ref: DeepBl4nderTUI | None = None

    def on_mount(self) -> None:
        self.app_ref = self.app  # type: ignore[assignment]

    def notify(self, message: str, *, title: str = "", severity: SeverityLevel = "information", timeout: float | None = 3.0, markup: bool = True) -> None:
        """Show notification."""
        if self.app_ref:
            self.app_ref.notify(message, title=title, severity=severity, timeout=timeout, markup=markup)
            