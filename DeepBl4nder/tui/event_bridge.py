"""Real-time event bridge: NOOA agent events -> in-process async bus.

The DeepBl4nder agents run on NOOA, which exposes a rich event pipeline
(``agent.event_manager.on(...)``): ``BeforeTurn``/``AfterTurn`` (one LLM
generation turn), ``LLMOutput``/``LLMComplete`` (model output / metadata),
``PythonOutput`` (executed code), ``Error``/``Feedback``, ``SystemPrompt``,
``TextOnlyReply``, ``Task``, ``LLMCallStart``/``LLMCallEnd`` and ``Message``.

We subscribe to these on every agent and normalize them into a single
``EventBroker`` stream whose events also carry the original pipeline events
(``step_started``, ``step_completed``, ``llm_call`` ...) emitted by the
``PipelineRunner``. The TUI console subscribes once to the broker and renders
live what the agents are doing - opencode-style.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Callable

_PY_CAP = 4000  # Cap per-line payloads to keep the log responsive.
_DATA_CAP = 1200


def _stable_hash(text: str) -> str:
    """Short stable fingerprint used to deduplicate identical system prompts."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


@dataclass
class StreamEvent:
    """One normalized event on the broker stream.

    ``actor`` is the agent slug (``director``, ``blender`` ...) or ``None`` for
    pipeline-level events. ``content`` holds a single-line display payload;
    richer structured data lives in ``meta``.
    """

    seq: int
    ts: float
    kind: str
    actor: str | None
    content: str
    meta: dict[str, Any] = field(default_factory=dict)
    production_id: str | None = None


def _snip(text: str, limit: int) -> str:
    """Truncate a payload to a single printable line."""
    compact = " ".join((text or "").splitlines())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}... ({len(compact)} chars)"


def _g(event: Any, name: str, default: Any = "") -> Any:
    """Read an optional attribute, returning ``default`` when absent/None."""
    value = getattr(event, name, None)
    return default if value is None else value


def _real_last_call(agent: Any) -> dict[str, str]:
    """Vainqueur réel du dernier appel LLM d'un agent (rotation).

    Lit ``_get_last_call_info`` de l'agent (``last_provider_id`` /
    ``last_model`` du routeur) ; vide tant qu'aucun appel n'a réussi.
    """
    getter = getattr(agent, "_get_last_call_info", None)
    if not callable(getter):
        return {}
    try:
        return getter()
    except Exception:  # noqa: BLE001 - l'info d'affichage ne doit jamais casser le flux
        return {}


class EventBroker:
    """In-process async pub/sub with a replayable ring buffer."""

    def __init__(self, history_size: int = 1000) -> None:
        self._subscribers: list[tuple[asyncio.Queue[StreamEvent], str | None]] = []
        self._history: deque[StreamEvent] = deque(maxlen=history_size)
        self._seq = 0

    def publish(self, event: StreamEvent) -> None:
        """Publish an event to all subscribers (non-blocking)."""
        self._seq += 1
        event.seq = self._seq
        self._history.append(event)
        for queue, pid in self._subscribers:
            if pid is None or event.production_id is None or event.production_id == pid:
                queue.put_nowait(event)

    async def subscribe(
        self, production_id: str | None = None
    ) -> asyncio.Queue[StreamEvent]:
        """Subscribe to the stream, preloaded with matching history."""
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        for event in self._history:
            if production_id is None or event.production_id == production_id:
                queue.put_nowait(event)
        self._subscribers.append((queue, production_id))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[StreamEvent]) -> None:
        self._subscribers = [q for q, _ in self._subscribers if q is not queue]

    def history(self, production_id: str | None = None) -> list[StreamEvent]:
        return [
            e
            for e in self._history
            if production_id is None or e.production_id == production_id
        ]


def attach_agent_bridge(
    *,
    agent: Any,
    actor: str,
    broker: EventBroker,
    production_id: Callable[[], str | None],
) -> None:
    """Subscribe a NOOA agent's event manager to the broker.

    Handlers are fire-and-forget (``put_nowait``) so agent execution never
    blocks on the UI. Missing event manager (stub agents) is tolerated.
    """
    event_manager = getattr(agent, "event_manager", None)
    if event_manager is None:
        return

    now = time.time

    def emit(kind: str, content: str, meta: dict[str, Any] | None = None) -> None:
        broker.publish(
            StreamEvent(
                seq=0,
                ts=now(),
                kind=kind,
                actor=actor,
                content=content,
                meta=meta or {},
                production_id=production_id(),
            )
        )

    def on_turn(event: Any, *, start: bool) -> None:
        turn, method = event.turn_number, event.method_name
        if start:
            emit(
                "turn_start",
                f"Turn {turn} started - {method} ({event.strategy})",
                {"turn": turn, "method": method, "strategy": event.strategy},
            )
        else:
            status = (
                f"failed ({event.exception_type})"
                if event.success is False
                else "done" if event.is_final else "more turns expected"
            )
            emit(
                "turn_end",
                f"Turn {turn} finished ({status})",
                {"turn": turn, "is_final": event.is_final, "success": event.success,
                 "exception_type": event.exception_type},
            )

    def on_complete(event: Any) -> None:
        cost = _g(event, "cost_usd", 0.0) or 0.0
        reasoning = _g(event, "reasoning_content")
        tool_calls = _g(event, "tool_calls", []) or []
        dynamic = _g(event, "dynamic_context")
        # Le vainqueur réel du routeur prime sur le ``model_name`` statique que
        # NOOA recopie depuis la config (``router.model``) : la rotation est
        # ainsi visible dans le flux, pas seulement en fin d'étape.
        real = _real_last_call(agent)
        real_model = real.get("model") or _g(event, "model_name") or ""
        meta: dict[str, Any] = {
            "model": real_model,
            "tokens": event.completion_tokens,
            "prompt_tokens": event.prompt_tokens,
            "cached_tokens": _g(event, "cached_tokens", 0),
            "cost_usd": cost,
            "reasoning_tokens": _g(event, "reasoning_tokens", 0),
            "generation_id": _g(event, "generation_id", ""),
            "tool_calls": tool_calls,
            "dynamic_context": dynamic,
            "dynamic_context_len": len(dynamic),
        }
        if real.get("provider"):
            meta["provider"] = real["provider"]
        name = str(_g(event, "method_name") or actor)
        summary = f"{name} -> {real_model or 'unknown'}"
        if cost:
            summary += f" (${cost:.4f}, {event.completion_tokens} tokens)"
        if reasoning:
            emit("reasoning", _snip(reasoning, 1200),
                 {"model": real_model, "chars": len(reasoning), "_full": reasoning})
        for call in tool_calls:
            fn = call.get("function_name", call.get("name", "tool"))
            args = str(call.get("arguments", ""))
            emit("tool_call", f"called {fn}", {"arguments": _snip(args, 600), "_full": args, "tool": fn})
        if dynamic:
            emit("context", f"context block: {len(dynamic)} chars injected",
                 {"chars": len(dynamic), "model": real_model, "_full": dynamic})
        emit("llm_complete", summary, meta)

    def on_python(event: Any) -> None:
        stdout, stderr = _g(event, "stdout"), _g(event, "stderr")
        if stdout:
            emit("python_output", f"stdout: {_snip(stdout, _PY_CAP)}",
                 {"channel": "stdout", "_full": stdout})
        if stderr:
            emit("python_output", f"stderr: {_snip(stderr, _PY_CAP)}",
                 {"channel": "stderr", "_full": stderr})
        error = _g(event, "error")
        if error:
            emit("error", f"execution error: {_snip(error, 600)}", {"channel": "exec", "_full": error})

    last_sys_hash = ""

    def on_system_prompt(event: Any) -> None:
        nonlocal last_sys_hash
        content = _g(event, "content")
        digest = _stable_hash(content) if content else ""
        if digest and digest == last_sys_hash:
            emit("system_prompt_cached", f"system prompt cached ({len(content)} chars)",
                 {"chars": len(content), "hash": digest})
            return
        if content:
            last_sys_hash = digest
        first_line = next((ln for ln in content.splitlines() if ln.strip()), "") if content else ""
        emit("system_prompt", f"system prompt: {len(content)} chars",
             {"chars": len(content), "first_line": first_line[:160], "_full": content})

    def on_text_reply(event: Any) -> None:
        content = _g(event, "content")
        consecutive = _g(event, "consecutive_text_only", 0)
        summary = f"text-only reply ({_g(event, 'route', '')})"
        if consecutive and consecutive > 1:
            summary += f" x{consecutive}"
        emit("text_reply", summary,
             {"chars": len(content), "route": _g(event, "route", ""),
              "consecutive": consecutive, "_full": content})

    def on_call_end(event: Any) -> None:
        ok = "ok" if event.success else f"error: {event.exception_type}"
        emit("call_end", f"model replied ({ok})", {"success": event.success})

    _HANDLERS: dict[str, Callable[[Any], None]] = {
        "BeforeTurn": partial(on_turn, start=True),
        "AfterTurn": partial(on_turn, start=False),
        "LLMOutput": lambda e: emit("output", _snip(_g(e, "content"), _DATA_CAP) or "(empty output)",
                                    {"content_length": len(_g(e, "content")), "_full": _g(e, "content")}),
        "LLMComplete": on_complete,
        "PythonOutput": on_python,
        "Error": lambda e: emit("error", _snip(_g(e, "content"), _DATA_CAP)),
        "Feedback": lambda e: emit("feedback", _snip(_g(e, "content"), _DATA_CAP)),
        "Message": lambda e: emit("message", _snip(_g(e, "content"), _DATA_CAP)),
        "Task": lambda e: emit("task", _snip(_g(e, "prompt"), _DATA_CAP)),
        "LLMCallStart": lambda e: emit(
            "call_start", f"waiting on model - {e.method_name} (turn {e.turn_number})",
            {"turn": e.turn_number, "method": e.method_name}),
        "LLMCallEnd": on_call_end,
        "SystemPrompt": on_system_prompt,
        "TextOnlyReply": on_text_reply,
    }

    for event_type, handler in _HANDLERS.items():
        try:
            event_manager.on(event_type, handler)
        except Exception:  # noqa: BLE001 - observer must never break the agent
            continue
