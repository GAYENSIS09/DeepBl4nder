from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from DeepBl4nder.llm.interface import LLMClient


class _FakeServer:
    base_url = "http://127.0.0.1:8080/v1"
    current_model = None

    async def ensure_model(self, model: Any) -> None:
        self.current_model = model

    async def close(self) -> None:
        return None


class _FakeCascade:
    def __init__(self) -> None:
        self.classify_calls: list[tuple[str, list[dict[str, Any]]]] = []
        self.model = SimpleNamespace(id="qwen3-4b")

    def classify(self, task_text: str, messages: list[dict[str, Any]]) -> Any:
        self.classify_calls.append((task_text, messages))
        return SimpleNamespace(value="general")

    def select_model(self, category: Any) -> Any:
        return self.model

    def record_outcome(self, model_id: str, success: bool, quality: float | None = None) -> None:
        return None

    def escalate(self, current: Any, category: Any) -> Any:
        return None

    def stats(self) -> dict[str, Any]:
        return {"total": 0, "by_model": {}}


class _FakeLocalClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(messages)
        return {"choices": [{"message": {"content": "ok"}}]}


@pytest.mark.parametrize("messages", [None, []])
def test_acall_defaults_empty_or_none_messages(
    monkeypatch: pytest.MonkeyPatch,
    messages: list[dict[str, Any]] | None,
) -> None:
    cascade = _FakeCascade()
    client = LLMClient(server=_FakeServer(), cascade=cascade)
    local_client = _FakeLocalClient()
    monkeypatch.setattr(client, "_get_client", lambda: local_client)

    result = asyncio.run(client.acall(messages=messages))

    assert result == "ok"
    expected = [{"role": "user", "content": ""}]
    assert local_client.calls == [expected]
    assert cascade.classify_calls == [("", expected)]
