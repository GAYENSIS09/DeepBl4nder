"""Live, in-process LLM metrics + persistent JSONL span recording.

This is the small, always-on observability sink that connects the router /
agent event stream to both:
  - a live, thread-safe accumulator that the TUI reads each render (tokens,
    cost, latency, per-agent and per-model breakdowns), and
  - an optional append-only JSONL span file (``<data>/logs/llm_spans.jsonl``)
    for later analysis (plus optional Langfuse via ``ObservabilityPlugin``).

Everything here is best-effort: a metrics fault must never break the LLM call
path or the UI pump loop.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("DeepBl4nder.llm.metrics")


@dataclass
class _Span:
    agent: str
    step: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    success: bool
    cache_hit: bool
    error: str
    ts: float = field(default_factory=time.time)


class LLMMetrics:
    """Thread-safe live metrics accumulator with optional JSONL persistence."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._lock = threading.Lock()
        self._spans: list[_Span] = []
        self._by_agent: dict[str, dict[str, float | int]] = defaultdict(
            lambda: {"calls": 0, "tokens": 0, "cost": 0.0, "latency_ms": 0.0, "failures": 0}
        )
        self._by_model: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "tokens": 0, "cost": 0.0, "failures": 0}
        )
        self._latencies: list[float] = []
        self._span_file: Any = None
        self._init_span_file()

    def _init_span_file(self) -> None:
        if not self._enabled:
            return
        try:
            log_dir = Path(os.environ.get("DeepBl4nder_DATA_DIR", "data")) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            self._span_file = open(log_dir / "llm_spans.jsonl", "a", encoding="utf-8")  # noqa: SIM115
        except Exception:  # noqa: BLE001
            self._span_file = None

    def record(
        self,
        *,
        agent: str,
        step: str,
        model: str,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        success: bool = True,
        cache_hit: bool = False,
        error: str = "",
    ) -> None:
        """Record one LLM call outcome (best-effort, never raises)."""
        try:
            self._record(
                _Span(
                    agent=agent or "unknown",
                    step=step or "",
                    model=model or "unknown",
                    provider=provider or "unknown",
                    input_tokens=max(0, int(input_tokens or 0)),
                    output_tokens=max(0, int(output_tokens or 0)),
                    cost_usd=max(0.0, float(cost_usd or 0.0)),
                    latency_ms=max(0.0, float(latency_ms or 0.0)),
                    success=bool(success),
                    cache_hit=bool(cache_hit),
                    error=error or "",
                )
            )
        except Exception:  # noqa: BLE001
            logger.debug("metrics record failed", exc_info=True)

    def _record(self, span: _Span) -> None:
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > 20000:  # born memory
                self._spans = self._spans[-20000:]
            agent = self._by_agent[span.agent]
            agent["calls"] += 1
            agent["tokens"] += span.input_tokens + span.output_tokens
            agent["cost"] += span.cost_usd
            agent["latency_ms"] += span.latency_ms
            if not span.success:
                agent["failures"] += 1
            model = self._by_model[span.model]
            model["calls"] += 1
            model["tokens"] += span.input_tokens + span.output_tokens
            model["cost"] += span.cost_usd
            model["provider"] = span.provider
            if not span.success:
                model["failures"] += 1
            self._latencies.append(span.latency_ms)
            if len(self._latencies) > 5000:
                self._latencies = self._latencies[-5000:]
        self._write_span(span)

    def _write_span(self, span: _Span) -> None:
        if self._span_file is None:
            return
        try:
            line = json.dumps(
                {
                    "agent": span.agent,
                    "step": span.step,
                    "model": span.model,
                    "provider": span.provider,
                    "input_tokens": span.input_tokens,
                    "output_tokens": span.output_tokens,
                    "cost_usd": span.cost_usd,
                    "latency_ms": span.latency_ms,
                    "success": span.success,
                    "cache_hit": span.cache_hit,
                    "error": span.error,
                    "timestamp": span.ts,
                },
                ensure_ascii=False,
            ) + "\n"
            self._span_file.write(line)
            self._span_file.flush()
        except Exception:  # noqa: BLE001
            pass

    def snapshot(self) -> dict[str, Any]:
        """Consistent, cheap snapshot for the UI (per-agent / per-model)."""
        with self._lock:
            lat = self._latencies
            avg_lat = sum(lat) / len(lat) if lat else 0.0
            p50 = _percentile(lat, 0.50)
            p95 = _percentile(lat, 0.95)
            total_tokens = sum(
                int(v["tokens"]) for v in self._by_agent.values()
            )
            total_cost = sum(float(v["cost"]) for v in self._by_agent.values())
            total_calls = sum(int(v["calls"]) for v in self._by_agent.values())
            total_failures = sum(
                int(v["failures"]) for v in self._by_agent.values()
            )
            by_agent = {
                k: {
                    "calls": int(v["calls"]),
                    "tokens": int(v["tokens"]),
                    "cost": round(float(v["cost"]), 4),
                    "avg_latency_ms": round(
                        float(v["latency_ms"]) / int(v["calls"]) if v["calls"] else 0.0, 1
                    ),
                    "failures": int(v["failures"]),
                }
                for k, v in self._by_agent.items()
            }
            by_model = {
                k: {
                    "calls": int(v["calls"]),
                    "tokens": int(v["tokens"]),
                    "cost": round(float(v["cost"]), 4),
                    "provider": v["provider"],
                    "failures": int(v["failures"]),
                }
                for k, v in self._by_model.items()
            }
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "total_failures": total_failures,
            "success_rate": round((total_calls - total_failures) / total_calls, 3)
            if total_calls
            else 1.0,
            "avg_latency_ms": round(avg_lat, 1),
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "by_agent": by_agent,
            "by_model": by_model,
        }

    def flush(self) -> None:
        if self._span_file is not None:
            try:
                self._span_file.flush()
            except Exception:  # noqa: BLE001
                pass


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))
    return round(ordered[idx], 1)


# Shared singleton used everywhere (router, event bridge, TUI).
_metrics: LLMMetrics | None = None
_metrics_lock = threading.Lock()


def get_metrics() -> LLMMetrics:
    """Return the process-wide LLM metrics singleton."""
    global _metrics
    if _metrics is None:
        with _metrics_lock:
            if _metrics is None:
                _metrics = LLMMetrics()
    return _metrics


def reset_metrics_for_tests() -> None:
    """Drop the singleton (tests)."""
    global _metrics
    with _metrics_lock:
        _metrics = None
