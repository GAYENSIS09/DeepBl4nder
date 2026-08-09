"""Serveur HTTP minimal (stdlib) : gateway DeepBlender.

Routes de base : /health, /version, /status, /validate, /budget, /events
(flux SSE temps réel). Le serveur n'exige aucune dépendance externe et reste
compatible avec la topologie docker-compose (gateway sur le port 8000).

Observabilité temps réel : le bus `EventBus` et le `BudgetTracker` peuvent
être injectés via `create_server` ; l'alerte budget est publiée sur le bus
dès le dépassement (objectif ADD : < 30 s).

CORS : autorise le frontend Next.js (par défaut http://localhost:3000).
"""

from __future__ import annotations

import json
import os
import queue
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from deepblender import __version__
from deepblender.blender.bridge import BlenderBridge
from deepblender.codegen.validator import ASTValidator
from deepblender.production.budget import BudgetTracker
from deepblender.production.events import EventBus
from deepblender.plugins.registry import PluginRegistry
from deepblender.plugins.render_farm import RenderFarmPlugin
from deepblender.plugins.tools import ToolRegistry
from deepblender.skills.registry import get_default_registry


# CORS configuration
CORS_ORIGIN = os.environ.get("DEEPBLENDER_CORS_ORIGIN", "http://localhost:3000")
CORS_HEADERS = {
    "Access-Control-Allow-Origin": CORS_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Credentials": "true",
}


class DeepBlenderHandler(BaseHTTPRequestHandler):
    """Gère les requêtes HTTP de la gateway."""

    server_version = f"DeepBlender/{__version__}"
    protocol_version = "HTTP/1.1"

    def _cors_headers(self) -> None:
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._json(HTTPStatus.OK, {
                "name": "DeepBlender API",
                "version": __version__,
                "docs": "/status",
                "frontend": "http://localhost:3000",
            })
        elif self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
        elif self.path == "/version":
            self._json(HTTPStatus.OK, {"version": __version__})
        elif self.path == "/status":
            registry = get_default_registry()
            bridge = BlenderBridge()
            plugin_registry = PluginRegistry()
            farm = plugin_registry.get("render-farm")
            self._json(
                HTTPStatus.OK,
                {
                    "skills": [info.name for info in registry.discover()],
                    "plugins": plugin_registry.discover(),
                    "tools": ToolRegistry().names(),
                    "blender": bridge.available(),
                    "worker_count": farm.worker_count(),
                    "gpu_count": farm.gpu_count(),
                },
            )
        elif self.path == "/plugins":
            plugin_registry = PluginRegistry()
            self._json(HTTPStatus.OK, {"plugins": plugin_registry.discover()})
        elif self.path == "/skills":
            self._json(
                HTTPStatus.OK,
                {"skills": [{"name": info.name, "description": info.description} for info in get_default_registry().discover()]},
            )
        elif self.path == "/workers":
            plugin_registry = PluginRegistry()
            farm = plugin_registry.get("render-farm")
            self._json(
                HTTPStatus.OK,
                {
                    "workers": [{"id": w.id, "kind": w.kind, "created_at": w.created_at} for w in farm._get_scheduler().workers()],
                    "worker_count": farm.worker_count(),
                    "gpu_count": farm.gpu_count(),
                },
            )
        elif self.path == "/tools":
            self._json(
                HTTPStatus.OK,
                {
                    "tools": [
                        {"name": tool.name, "description": tool.description}
                        for tool in ToolRegistry().tools()
                    ],
                },
            )
        elif self.path == "/budget":
            self._serve_budget()
        elif self.path == "/events":
            self._serve_events()
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/validate":
            payload = self._read_json()
            source = payload.get("source", "") if isinstance(payload, dict) else ""
            report = ASTValidator().validate(source)
            self._json(
                HTTPStatus.OK,
                {
                    "ok": report.ok,
                    "errors": report.errors,
                    "imports": report.imports,
                },
            )
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _serve_budget(self) -> None:
        budget = getattr(self.server, "budget", None)
        if budget is None:
            self._json(HTTPStatus.NOT_IMPLEMENTED, {"error": "budget tracker disabled"})
            return
        report = budget.report()
        self._json(HTTPStatus.OK, {**report, "over_budget": budget.over_budget()})

    def _serve_events(self) -> None:
        """Flux SSE : événements temps réel du bus (observabilité ADD)."""
        bus = getattr(self.server, "bus", None)
        if bus is None:
            self._json(HTTPStatus.NOT_IMPLEMENTED, {"error": "event bus disabled"})
            return
        subscriber = bus.subscribe()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors_headers()
        self.end_headers()
        try:
            while True:
                try:
                    event = subscriber.get(timeout=15)
                except queue.Empty:
                    self._write_event({"type": "ping"})
                    continue
                self._write_event(event)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            bus.unsubscribe(subscriber)

    def _write_event(self, payload: dict[str, Any]) -> None:
        frame = f"data: {json.dumps(payload)}\n\n".encode("utf-8")
        self.wfile.write(frame)
        self.wfile.flush()

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Silence les logs par requête (déjà couverts par le tracing NOOA)."""


class DeepBlenderServer(ThreadingHTTPServer):
    """Serveur typé portant le bus d'événements et le tracker de budget."""

    bus: EventBus | None = None
    budget: BudgetTracker | None = None


def create_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    bus: EventBus | None = None,
    budget: BudgetTracker | None = None,
) -> DeepBlenderServer:
    server = DeepBlenderServer((host, port), DeepBlenderHandler)
    server.bus = bus
    server.budget = budget
    return server


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    default_budget = float(os.environ.get("DEEPBENDER_BUDGET", "1.0"))
    bus = EventBus()
    budget = BudgetTracker(budget=default_budget, run_id="gateway")
    budget.subscribe(lambda alert: bus.publish({"type": "budget_alert", **asdict(alert)}))
    server = create_server(host, port, bus=bus, budget=budget)
    print(f"DeepBlender gateway on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
