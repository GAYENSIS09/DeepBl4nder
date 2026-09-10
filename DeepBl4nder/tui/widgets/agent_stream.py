"""Live agent stream widget - renders NOOA bridge events with brand colors.

Design (expert production console):
- Le burst de fin d'appel LLM est consolidé : reasoning/tool_call/context ne
  font plus 5 lignes simultanées, ils sont pliés dans une seule ligne de tour
  ``llm_complete`` (détail complet disponible dans l'overlay ``v``).
- Le contenu produit (``output``) est révélé progressivement (fractionnement
  avec petit délai) pour un rendu "streaming" même si NOOA émet une seule fois.
"""

from __future__ import annotations

import asyncio
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

# Événements pliés dans la ligne de tour ``llm_complete`` : ils ne sont plus
# écrits individuellement (c'était le "tout d'un coup" en fin de génération).
_TURN_FOLD = {
    "reasoning", "tool_call", "context", "system_prompt", "system_prompt_cached",
    "agent_call_start", "agent_call_end",
}

_KIND_STYLES: dict[str, tuple[str, str]] = {
    "output": ("", theme.TEXT),
    "reasoning": ("thought", theme.ACCENT),
    "system_prompt": ("sys", theme.TEXT_DIM),
    "system_prompt_cached": ("sys", theme.TEXT_DIM),
    "context": ("ctx", theme.TEXT_DIM),
    "context_compacted": ("ctx", theme.WARNING),
    "text_reply": ("text", theme.WARNING),
    "python_output": ("shell", theme.TEXT_DIM),
    "tool_call": ("tool", theme.INFO),
    "tool_result": ("result", theme.INFO),
    "agent_call_start": ("method", theme.INFO),
    "agent_call_end": ("method", theme.INFO),
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


def _snip_preview(value: str, limit: int = 240) -> str:
    compact = " ".join((value or "").splitlines())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}... ({len(compact)} chars)"


def _turn_details(meta: dict) -> list[str]:
    """Lignes compactes du tour, consolidées depuis reasoning/tool_call/context."""
    lines: list[str] = []
    tokens = meta.get("tokens")
    if isinstance(tokens, int):
        parts = [f"tokens {meta.get('prompt_tokens', 0)} + {tokens}"]
        if meta.get("reasoning_tokens"):
            parts.append(f"reasoning {meta['reasoning_tokens']}")
        lines.append(" ".join(parts))
    if meta.get("cached_tokens"):
        lines.append(f"cached {meta['cached_tokens']}")
    if meta.get("dynamic_context_len"):
        lines.append(f"context {meta['dynamic_context_len']} chars")
    if meta.get("cost_usd"):
        lines.append(f"cost ${meta['cost_usd']:.4f}")
    tools = meta.get("tool_calls") or []
    if tools:
        names = ", ".join(str(c.get("function_name", c.get("name", "tool"))) for c in tools[:3])
        lines.append(f"{len(tools)} tool call(s): {names}")
    reasoning = meta.get("reasoning_preview")
    if reasoning:
        lines.append(f"thought: {reasoning}")
    return lines


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
    if kind == "llm_complete":
        return _turn_details(meta)
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
    if kind == "context_compacted" and meta.get("events"):
        lines = [f"range {meta['events']}"]
        summary = meta.get("summary_text") or ""
        if summary:
            lines.append(f"summary: {summary[:200]}")
        else:
            lines.append("no summary text (pure truncation)")
        return lines
    if kind == "agent_call_start":
        lines = [f"call {meta.get('call_id', '')[:8]}"]
        if meta.get("needs_generation"):
            lines.append("LLM method")
        if not meta.get("top_level"):
            lines.append("nested")
        return lines
    if kind == "agent_call_end" and meta.get("method"):
        return [f"call {meta.get('call_id', '')[:8]}"]
    if kind == "tool_result":
        return [f"value: {meta.get('_full', '')[:400]}"]
    return []


class AgentStream(Widget):
    """Borderless live stream of all agent + pipeline activity."""

    count: reactive[int] = reactive(0)
    _PLACEHOLDER = "Waiting for a brief. Type your idea in the bar above and press Run."

    _OUTPUT_CHUNK = 96
    _OUTPUT_DELAY = 0.018

    def __init__(self, *, id: str = "agent-stream") -> None:
        super().__init__(id=id)
        self._log: RichLog | None = None
        self._text_buffer: deque[str] = deque(maxlen=2000)
        self._output_worker: asyncio.Task | None = None

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

        if event.kind == "output":
            self._start_output_stream(event)
            return
        if event.kind in _TURN_FOLD:
            return

        for line in render_event(event):
            self._log.write(line)
            self._text_buffer.append(str(line))
        self.count += 1

    # ========== progressive output rendering ==========

    def _start_output_stream(self, event: StreamEvent) -> None:
        """Reveal ``output`` content progressively (fractionné + délai).

        NOOA n'émet ``LLMOutput`` qu'une seule fois en fin de génération ;
        on simule un rendu "streaming" côté affichage pour un flux vivant.
        """
        if self._output_worker is not None and not self._output_worker.done():
            self._output_worker.cancel()
        self._output_worker = asyncio.create_task(self._stream_output(event))

    async def _stream_output(self, event: StreamEvent) -> None:
        if self._log is None:
            return
        head = _head(_stamp(event.ts), event.actor, "", theme.TEXT)
        head.append(event.content, style=theme.TEXT)
        text = str(event.content) or ""
        head_plain = str(head)
        self._log.write(head)
        self._text_buffer.append(head_plain)
        self.count += 1

        for start in range(0, len(text), self._OUTPUT_CHUNK):
            piece = text[start:start + self._OUTPUT_CHUNK]
            wrapper = Text(f"  {piece}", style=theme.TEXT)
            self._log.write(wrapper)
            self._text_buffer.append(str(wrapper))
            self.count += 1
            await asyncio.sleep(self._OUTPUT_DELAY)

    def _write_placeholder(self) -> None:
        self.write_line(self._PLACEHOLDER)

    def clear_stream(self) -> None:
        if self._output_worker is not None and not self._output_worker.done():
            self._output_worker.cancel()
            self._output_worker = None
        if self._log is not None:
            self._log.clear()
        self.count = 0
        self._text_buffer.clear()
        self._write_placeholder()

    def export_text(self) -> str:
        """Entière sortie actuelle du flux (texte brut, pour copie presse-papiers)."""
        return "\n".join(self._text_buffer)