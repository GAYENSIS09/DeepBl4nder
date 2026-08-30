"""Event detail overlay - full content of a stream event (console: touche ``v``).

Mode compact dans le flux, détail intégral sur demande : contenu du message
(``meta._full``, fallback ``content``) + métadonnées brutes. Navigation
``up``/``down`` dans l'anneau d'événements, ``escape``/``q`` ferme.
"""

from __future__ import annotations

from collections import deque

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from DeepBl4nder.tui import theme
from DeepBl4nder.tui.event_bridge import StreamEvent
from DeepBl4nder.tui.widgets.agent_stream import (
    _KIND_STYLES,
    _actor_color,
    _actor_tag,
    _stamp,
)

_META_HIDDEN = {"_full", "_snip"}


class EventDetailScreen(ModalScreen[None]):
    """Full content of a selected stream event (scrollable overlay)."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("q", "close", "Close", show=False),
        Binding("up", "up", "Previous", show=False),
        Binding("down", "down", "Next", show=False),
    ]

    def __init__(
        self,
        events: deque[StreamEvent],
        *,
        index: int = 0,
        name: str = "event-detail",
    ) -> None:
        super().__init__(name=name)
        self._events = events
        self._index = index

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="event-detail-scroll"):
            yield Static(id="event-detail-body")

    def on_mount(self) -> None:
        self._populate()

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_up(self) -> None:
        if self._events:
            self._index = (self._index - 1) % len(self._events)
            self._populate()

    def action_down(self) -> None:
        if self._events:
            self._index = (self._index + 1) % len(self._events)
            self._populate()

    def _populate(self) -> None:
        if not self._events:
            return
        event = self._events[self._index % len(self._events)]
        kind = event.kind
        tag, style = _KIND_STYLES.get(kind, ("", theme.TEXT_MUTED))
        text = Text()
        text.append(f"{_stamp(event.ts)} ", style=theme.TEXT_DIM)
        if event.actor:
            text.append(f"[{_actor_tag(event.actor)}] ", style=_actor_color(event.actor))
        if tag:
            text.append(f"({tag}) ", style=style)
        text.append(kind, style=style + " bold")
        text.append("\n\n")

        full = (event.meta or {}).get("_full")
        full = full if isinstance(full, str) and full.strip() else event.content
        content_style = theme.TEXT if kind in ("output", "message") else style
        for line in full.splitlines() or [""]:
            text.append(line or " ", style=content_style)
            text.append("\n")
        text.append("\n")

        meta = {key: value for key, value in (event.meta or {}).items() if key not in _META_HIDDEN}
        if meta:
            text.append("— meta —\n", style=theme.TEXT_MUTED + " bold")
            for key in meta:
                text.append(f"  {key}: {meta[key]}\n", style=theme.TEXT_DIM)

        self.query_one("#event-detail-body", Static).update(text)
        self.query_one("#event-detail-scroll", VerticalScroll).scroll_home(animate=False)