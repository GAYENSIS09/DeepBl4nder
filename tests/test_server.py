"""Gateway HTTP minimale : /health, /version, /status, /validate, /budget, /events."""

from __future__ import annotations

import http.client
import json
import threading
from collections.abc import Iterator
from dataclasses import asdict

import pytest

from deepblender import __version__
from deepblender.api.server import DeepBlenderHandler, create_server
from deepblender.blender.bridge import BlenderBridge
from deepblender.production.budget import BudgetTracker
from deepblender.production.events import EventBus
from deepblender.skills.registry import SkillRegistry


@pytest.fixture
def base_url() -> Iterator[str]:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), DeepBlenderHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    thread.join(timeout=5)


def _get(url: str, path: str) -> tuple[int, str, str]:
    conn = http.client.HTTPConnection(url.removeprefix("http://"))
    conn.request("GET", path)
    response = conn.getresponse()
    body = response.read().decode("utf-8")
    status = response.status
    ctype = response.getheader("Content-Type", "")
    conn.close()
    return status, body, ctype


def test_health(base_url: str) -> None:
    status, body, _ = _get(base_url, "/health")
    assert status == 200
    assert json.loads(body)["status"] == "ok"


def test_version(base_url: str) -> None:
    status, body, _ = _get(base_url, "/version")
    assert status == 200
    assert json.loads(body)["version"] == __version__


def test_status_reports_skills_and_blender(base_url: str) -> None:
    status, body, _ = _get(base_url, "/status")
    assert status == 200
    payload = json.loads(body)
    expected = {info.name for info in SkillRegistry().discover()}
    assert expected <= set(payload["skills"])
    assert payload["blender"] is BlenderBridge().available()
    assert isinstance(payload["plugins"], list)
    assert "render" in payload["tools"]


def test_plugins_endpoint(base_url: str) -> None:
    status, body, _ = _get(base_url, "/plugins")
    assert status == 200
    plugins = json.loads(body)["plugins"]
    assert any(plugin["name"] == "blender" for plugin in plugins)
    assert all("available" in plugin for plugin in plugins)


def test_tools_endpoint(base_url: str) -> None:
    status, body, _ = _get(base_url, "/tools")
    assert status == 200
    tools = json.loads(body)["tools"]
    names = {tool["name"] for tool in tools}
    assert names == {"inspect_scene", "load_asset", "save_blend", "render", "inspect_render", "create_audio", "compose", "export"}
    assert all(tool["description"] for tool in tools)


def test_skills_endpoint_lists_full_catalogue(base_url: str) -> None:
    status, body, _ = _get(base_url, "/skills")
    assert status == 200
    skills = json.loads(body)["skills"]
    names = {skill["name"] for skill in skills}
    assert len(names) >= 25
    assert {"storytelling", "sound-design", "translation", "rigging", "subtitles"} <= names


def test_workers_endpoint(base_url: str) -> None:
    status, body, _ = _get(base_url, "/workers")
    assert status == 200
    payload = json.loads(body)
    assert payload["worker_count"] >= 1
    assert payload["gpu_count"] >= 0
    assert all("id" in worker and "kind" in worker for worker in payload["workers"])


def test_index_html(base_url: str) -> None:
    status, body, ctype = _get(base_url, "/")
    assert status == 200
    assert "application/json" in ctype
    payload = json.loads(body)
    assert payload["name"] == "DeepBlender API"
    assert "version" in payload


def test_validate_endpoint(base_url: str) -> None:
    conn = http.client.HTTPConnection(base_url.removeprefix("http://"))
    payload = json.dumps({"source": "import os\n"}).encode("utf-8")
    conn.request("POST", "/validate", body=payload, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    assert response.status == 200
    result = json.loads(response.read().decode("utf-8"))
    assert result["ok"] is False
    conn.close()


def test_unknown_route(base_url: str) -> None:
    status, body, _ = _get(base_url, "/nope")
    assert status == 404
    assert "error" in json.loads(body)


@pytest.fixture
def stateful_url() -> Iterator[tuple[str, EventBus, BudgetTracker]]:
    bus = EventBus()
    budget = BudgetTracker(budget=1.0, run_id="run-1")
    budget.subscribe(lambda alert: bus.publish({"type": "budget_alert", **asdict(alert)}))
    server = create_server("127.0.0.1", 0, bus=bus, budget=budget)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}", bus, budget
    server.shutdown()
    thread.join(timeout=5)


def test_budget_endpoint_reports(stateful_url: tuple[str, EventBus, BudgetTracker]) -> None:
    url, _, budget = stateful_url
    budget.add_llm(0.25)
    status, body, _ = _get(url, "/budget")
    assert status == 200
    payload = json.loads(body)
    assert payload["total"] == pytest.approx(0.25)
    assert payload["budget"] == 1.0
    assert payload["over_budget"] is False


def test_events_sse_streams_budget_alert(stateful_url: tuple[str, EventBus, BudgetTracker]) -> None:
    url, _, budget = stateful_url
    conn = http.client.HTTPConnection(url.removeprefix("http://"))
    conn.request("GET", "/events")
    response = conn.getresponse()
    assert response.status == 200
    assert "text/event-stream" in response.getheader("Content-Type", "")
    budget.add_llm(0.60)
    budget.add_render(0.50)
    line = response.readline()
    assert line.startswith(b"data: ")
    payload = json.loads(line.decode("utf-8")[len("data: "):])
    assert payload["type"] == "budget_alert"
    assert payload["overshoot"] == pytest.approx(0.1)
    conn.close()


def test_events_sse_disabled_on_plain_server(base_url: str) -> None:
    status, body, _ = _get(base_url, "/events")
    assert status == 501
    assert "error" in json.loads(body)
