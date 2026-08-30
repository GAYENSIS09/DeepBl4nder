"""Live agent stream widget - renders NOOA bridge events with brand colors."""

from __future__ import annotations

from collections import deque
from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import RichLog

from DeepBl4nder.tui import theme
from DeepBl4nder.tui.event_bridge import StreamEvent

_STEP_HEADERS = {
    "run_started", "step_started", "step_completed", "step_failed", "step_resumed",
    "revision_requested", "approval_required", "run_completed", "run_blocked",
    "run_failed", "run_cancelled", "budget_alert", "render_started",
    "render_completed", "patches_applied",
}

_KIND_STYLES: dict[str, tuple[str, str]] = {
    "output": ("", theme.TEXT),
    "reasoning": ("thought", theme.ACCENT),
    "system_prompt": ("sys", theme.TEXT_DIM),
    "system_prompt_cached": ("sys", theme.TEXT_DIM),
    "context": ("ctx", theme.TEXT_DIM),
    "text_reply": ("text", theme.WARNING),
    "python_output": ("shell", theme.TEXT_DIM),
    "tool_call": ("tool", theme.INFO),
    "llm_complete": ("done", theme.TEXT_DIM),
    "call_start": ("waiting", theme.TEXT_DIM),
    "call_end": ("replied", theme.TEXT_DIM),
    "turn_start": ("turn", theme.TEXT_DIM),
    "turn_end": ("turn", theme.TEXT_DIM),
    "feedback": ("feedback", theme.WARNING),
    "message": ("info", theme.TEXT),
    "skills_loaded": ("skills", theme.INFO),
    "plugin_used": ("plugin", theme.INFO),
    "error": ("error", theme.ERROR),
    "task": ("task", theme.TEXT_MUTED),
}


def _stamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def _actor_color(actor: str | None) -> str:
    return theme.ACTOR_COLORS.get(actor, theme.TEXT_MUTED) if actor else theme.TEXT_MUTED


def _actor_tag(actor: str | None) -> str:
    return theme.ACTOR_LABELS.get(actor, actor or "pipeline")


def _head(stamp: str, actor: str | None, prefix: str, style: str) -> Text:
    """Common stream line head: timestamp + actor tag + optional kind prefix."""
    text = Text()
    text.append(f"{stamp} ", style=theme.TEXT_DIM)
    if actor:
        text.append(f"[{_actor_tag(actor)}] ", style=_actor_color(actor))
    if prefix:
        text.append(f"({prefix}) ", style=style)
    return text


def render_event(event: StreamEvent) -> list[Text]:
    """Convert a normalized stream event into styled lines for the log."""
    kind, actor, stamp = event.kind, event.actor, _stamp(event.ts)

    if kind in _STEP_HEADERS:
        if actor:
            head = _head(stamp, actor, "", theme.TEXT_MUTED)
            head.append(event.content, style=theme.ACCENT)
            return [head]
        if kind in ("run_failed", "run_blocked"):
            style = theme.ERROR + " bold"
        elif kind == "budget_alert":
            style = theme.WARNING + " bold"
        else:
            style = theme.ACCENT + " bold"
        head = _head(stamp, None, "", "")
        head.append(event.content, style=style)
        return [head]

    prefix, style = _KIND_STYLES.get(kind, ("", theme.TEXT_MUTED))
    lines = [_head(stamp, actor, prefix, style)]
    lines[0].append(event.content, style=style)
    for detail in _detail_lines(event.meta or {}, kind):
        lines.append(Text(f"    {detail}", style=theme.TEXT_DIM))
    return lines


def _detail_lines(meta: dict, kind: str) -> list[str]:
    if kind == "output" and "content_length" in meta:
        return [f"{meta['content_length']} chars"]
    if kind == "llm_complete" and "tokens" in meta:
        lines = [
            f"tokens {meta.get('prompt_tokens', 0)} + {meta.get('tokens', 0)} "
            f"(reasoning {meta.get('reasoning_tokens', 0)})"
        ]
        if meta.get("cached_tokens"):
            lines.append(f"cached {meta['cached_tokens']}")
        if meta.get("dynamic_context_len"):
            lines.append(f"context {meta['dynamic_context_len']} chars")
        if meta.get("cost_usd"):
            lines.append(f"cost ${meta['cost_usd']:.4f}")
        return lines
    if kind == "context" and meta.get("chars"):
        return [f"{meta['chars']} chars injected to the model"]
    if kind in ("system_prompt", "system_prompt_cached") and "chars" in meta:
        lines = [f"{meta['chars']} chars"]
        first = meta.get("first_line") or ""
        if first:
            lines.append(f"first line: {first}")
        return lines
    if kind == "skills_loaded" and meta.get("skills"):
        return [f"loaded: {', '.join(meta['skills'])}"]
    if kind == "plugin_used" and meta.get("plugin") and meta.get("method"):
        return [f"{meta['plugin']}.{meta['method']}"]
    if kind == "tool_call" and meta.get("arguments"):
        return [f"  args: {meta['arguments']}"]
    return []


class AgentStream(Widget):
    """Borderless live stream of all agent + pipeline activity."""

    count: reactive[int] = reactive(0)
    _PLACEHOLDER = "Waiting for a brief. Type your idea in the bar above and press Run."

    def __init__(self, *, id: str = "agent-stream") -> None:
        super().__init__(id=id)
        self._log: RichLog | None = None
        self._text_buffer: deque[str] = deque(maxlen=2000)

    def compose(self) -> ComposeResult:
        self._log = RichLog(
            id="stream-log", markup=False, highlight=False,
            auto_scroll=True, max_lines=3000, wrap=True,
        )
        yield self._log

    def on_mount(self) -> None:
        if self._log is not None:
            self._log.clear()
        self._write_placeholder()

    def _timestamp_line(self, message: str, style: str = theme.TEXT_MUTED) -> Text:
        text = Text(f"{datetime.now().strftime('%H:%M:%S')} ", style=theme.TEXT_DIM)
        text.append(message, style=style)
        return text

    def write_line(self, message: str, style: str = theme.TEXT_MUTED) -> None:
        if self._log is None:
            return
        line = self._timestamp_line(message, style)
        self._log.write(line)
        self._text_buffer.append(str(line))

    def write_event(self, event: StreamEvent) -> None:
        if self._log is None:
            return
        for line in render_event(event):
            self._log.write(line)
            self._text_buffer.append(str(line))
        self.count += 1

    def _write_placeholder(self) -> None:
        self.write_line(self._PLACEHOLDER)

    def clear_stream(self) -> None:
        if self._log is not None:
            self._log.clear()
        self.count = 0
        self._text_buffer.clear()
        self._write_placeholder()

    def export_text(self) -> str:
        """Entière sortie actuelle du flux (texte brut, pour copie presse-papiers)."""
        return "\n".join(self._text_buffer)
