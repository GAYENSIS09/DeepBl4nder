"""ObservabilityPlugin : tracing LLM via Langfuse/OpenTelemetry.

Enregistre chaque appel LLM avec cout, latence, tokens, modele.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepblender.plugins.base import Plugin

logger = logging.getLogger("deepblender.plugins.observability")


@dataclass
class LLMSpan:
    """Span d'un appel LLM trace."""

    trace_id: str
    agent: str
    step: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    success: bool = True
    cache_hit: bool = False
    error: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "agent": self.agent,
            "step": self.step,
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "success": self.success,
            "cache_hit": self.cache_hit,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class ObservabilityPlugin(Plugin):
    """Tracing LLM via Langfuse (self-hosted) et/ou JSONL local."""

    name: str = "observability"
    description: str = "Observabilite LLM : Langfuse, OpenTelemetry, JSONL."
    _langfuse_client: Any = field(default=None, repr=False)
    _span_file: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._init_langfuse()
        self._init_span_file()

    def _init_langfuse(self) -> None:
        """Initialise Langfuse si configure."""
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        host = os.environ.get("LANGFUSE_HOST", "http://localhost:3001")

        if not (secret_key and public_key):
            logger.info("Langfuse non configure, tracing JSONL local uniquement")
            return

        try:
            from langfuse import Langfuse

            self._langfuse_client = Langfuse(
                secret_key=secret_key,
                public_key=public_key,
                host=host,
            )
            logger.info("Langfuse connecte: %s", host)
        except ImportError:
            logger.warning("langfuse non installe")
        except Exception as exc:
            logger.warning("Langfuse erreur: %s", exc)

    def _init_span_file(self) -> None:
        """Ouvre le fichier JSONL pour le tracing local."""
        log_dir = Path(os.environ.get("DEEPBLENDER_DATA_DIR", "data")) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        span_path = log_dir / "llm_spans.jsonl"
        try:
            self._span_file = open(span_path, "a", encoding="utf-8")
        except Exception:
            self._span_file = None

    def available(self) -> bool:
        return True

    def trace_llm_call(self, span: LLMSpan) -> None:
        """Trace un appel LLM."""
        # JSONL local (toujours)
        self._write_span(span)

        # Langfuse (si configure)
        if self._langfuse_client:
            try:
                self._langfuse_client.trace(
                    name=f"{span.agent}.{span.step}",
                    metadata={
                        "model": span.model,
                        "provider": span.provider,
                        "input_tokens": span.input_tokens,
                        "output_tokens": span.output_tokens,
                        "cost_usd": span.cost_usd,
                        "cache_hit": span.cache_hit,
                    },
                    session_id=span.trace_id,
                )
            except Exception as exc:
                logger.debug("Langfuse trace error: %s", exc)

    def _write_span(self, span: LLMSpan) -> None:
        """Ecrit un span en JSONL."""
        if self._span_file:
            try:
                line = json.dumps(span.to_dict(), ensure_ascii=False) + "\n"
                self._span_file.write(line)
                self._span_file.flush()
            except Exception:
                pass

    def get_spans(self, limit: int = 100) -> list[dict[str, Any]]:
        """Lit les derniers spans depuis le fichier JSONL."""
        span_path = Path(os.environ.get("DEEPBLENDER_DATA_DIR", "data")) / "logs" / "llm_spans.jsonl"
        if not span_path.exists():
            return []

        spans = []
        try:
            with open(span_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            spans.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            return []

        return spans[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Statistiques agrgees des appels LLM."""
        spans = self.get_spans(limit=10000)
        if not spans:
            return {"total_calls": 0}

        total_cost = sum(s.get("cost_usd", 0) for s in spans)
        total_tokens = sum(s.get("input_tokens", 0) + s.get("output_tokens", 0) for s in spans)
        avg_latency = sum(s.get("latency_ms", 0) for s in spans) / len(spans)
        success_rate = sum(1 for s in spans if s.get("success", True)) / len(spans)
        cache_hits = sum(1 for s in spans if s.get("cache_hit", False))

        by_model: dict[str, int] = {}
        for s in spans:
            model = s.get("model", "unknown")
            by_model[model] = by_model.get(model, 0) + 1

        return {
            "total_calls": len(spans),
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "avg_latency_ms": round(avg_latency, 1),
            "success_rate": round(success_rate, 3),
            "cache_hit_rate": round(cache_hits / len(spans), 3) if spans else 0,
            "by_model": by_model,
        }

    def flush(self) -> None:
        """Vide les buffers."""
        if self._langfuse_client:
            try:
                self._langfuse_client.flush()
            except Exception:
                pass
