"""Métriques LLM live : accumulateur, agrégations et écriture JSONL."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from DeepBl4nder.llm.metrics import LLMMetrics, get_metrics, reset_metrics_for_tests


def _span_file(tmp_path: Path) -> Path:
    return tmp_path / "logs" / "llm_spans.jsonl"


def test_record_and_snapshot(tmp_path: Path) -> None:
    m = LLMMetrics(enabled=True)
    m._span_file = None  # empêche l'écriture hors du dossier temporaire
    m.record(agent="director", step="plan_scene", model="gemini/gemini-3.6-flash",
             provider="gemini", input_tokens=100, output_tokens=50, cost_usd=0.01,
             latency_ms=500.0, success=True)
    m.record(agent="director", step="plan_scene", model="gemini/gemini-3.6-flash",
             provider="gemini", input_tokens=200, output_tokens=80, cost_usd=0.02,
             latency_ms=1500.0, success=True, cache_hit=True)
    m.record(agent="blender", step="build_script", model="groq/openai/gpt-oss-120b",
             provider="groq", input_tokens=10, output_tokens=5, cost_usd=0.001,
             latency_ms=300.0, success=False, error="boom")

    snap = m.snapshot()
    assert snap["total_calls"] == 3
    assert snap["total_failures"] == 1
    assert snap["success_rate"] == round(2 / 3, 3)
    assert snap["total_tokens"] == 100 + 50 + 200 + 80 + 10 + 5
    assert snap["total_cost_usd"] == round(0.031, 4)

    assert snap["by_agent"]["director"]["calls"] == 2
    assert snap["by_agent"]["director"]["tokens"] == 100 + 50 + 200 + 80
    assert snap["by_agent"]["blender"]["failures"] == 1

    assert snap["by_model"]["gemini/gemini-3.6-flash"]["provider"] == "gemini"
    assert snap["by_model"]["groq/openai/gpt-oss-120b"]["failures"] == 1

    assert snap["avg_latency_ms"] > 0
    assert snap["p50_latency_ms"] <= snap["p95_latency_ms"]


def test_jsonl_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DeepBl4nder_DATA_DIR", str(tmp_path))
    m = LLMMetrics(enabled=True)
    assert _span_file(tmp_path).exists()

    m.record(agent="qa", step="assess", model="openrouter/meta-llama/llama-3.3-70b-instruct",
             provider="openrouter", input_tokens=10, output_tokens=10,
             cost_usd=0.005, latency_ms=100.0, success=True)

    lines = [
        json.loads(ln)
        for ln in _span_file(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    ]
    assert len(lines) == 1
    assert lines[0]["agent"] == "qa"
    assert lines[0]["provider"] == "openrouter"
    assert lines[0]["input_tokens"] == 10


def test_record_never_raises(tmp_path: Path) -> None:
    m = LLMMetrics(enabled=True)
    m._span_file = None
    m.record(agent=None, step=123, model=None, provider=None)  # type: ignore[arg-type]
    assert m.snapshot()["total_calls"] == 1


def test_global_singleton(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DeepBl4nder_DATA_DIR", str(tmp_path))
    reset_metrics_for_tests()
    try:
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2
    finally:
        reset_metrics_for_tests()
