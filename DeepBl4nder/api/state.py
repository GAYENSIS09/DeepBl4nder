"""État partagé de l'API SaaS (moteur, sessions, clé secrète, worker).

Configuré une fois par `create_app` et lu par les dépendances
(`get_db`, `get_current_user`) sans passer par le `state` dynamique de
Starlette (typé, sans import circulaire).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_secret_key: str = ""


class WorkerStatus:
    """État du worker intégré (tâches asyncio lancées par l'API).

    Comptabilise les runs soumis, en cours, terminés et échoués ainsi que le
    dernier heartbeat, pour l'endpoint `GET /api/worker`.

    Un lock par projet (`_active_projects`) empêche les exécutions concurrentes
    du pipeline sur un même projet.
    """

    def __init__(self) -> None:
        self._running: dict[str, float] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._active_projects: set[str] = set()
        self._queued = 0
        self._processed = 0
        self._failed = 0
        self._last_heartbeat = time.time()

    def acquire(self, project_id: str) -> bool:
        """Tente de verrouiller un projet. Retourne True si le lock est acquis."""
        if project_id in self._active_projects:
            return False
        self._active_projects.add(project_id)
        return True

    def release(self, project_id: str) -> None:
        """Libère le verrou du projet."""
        self._active_projects.discard(project_id)

    def is_locked(self, project_id: str) -> bool:
        """True si le projet a déjà un run en cours."""
        return project_id in self._active_projects

    def submit(self) -> None:
        """Un run entre dans la file d'exécution."""
        self._queued += 1

    def start(self, production_id: str) -> None:
        """Le run démarre réellement sur le worker."""
        if self._queued > 0:
            self._queued -= 1
        self._running[production_id] = time.time()
        self._last_heartbeat = time.time()

    def register_task(self, production_id: str, task: asyncio.Task[None]) -> None:
        """Enregistre la tâche asyncio associée à une production."""
        self._tasks[production_id] = task

    def cancel_task(self, production_id: str) -> bool:
        """Annule la tâche asyncio d'une production. Retourne True si annulée."""
        task = self._tasks.pop(production_id, None)
        if task is not None and not task.done():
            task.cancel()
            return True
        return False

    def finish(self, production_id: str, *, failed: bool = False) -> None:
        """Le run se termine (succès ou échec)."""
        self._running.pop(production_id, None)
        self._processed += 1
        if failed:
            self._failed += 1
        self._last_heartbeat = time.time()

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": "online" if (self._running or self._queued or self._processed) else "idle",
            "queue_depth": self._queued,
            "running": [
                {"production_id": production_id, "since": since}
                for production_id, since in self._running.items()
            ],
            "processed": self._processed,
            "failed": self._failed,
            "last_heartbeat": self._last_heartbeat,
        }


def configure(engine: Engine, session_factory: sessionmaker[Session], secret_key: str) -> None:
    global _engine, _session_factory, _secret_key
    _engine = engine
    _session_factory = session_factory
    _secret_key = secret_key


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("API not configured: call create_app() first")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        raise RuntimeError("API not configured: call create_app() first")
    return _session_factory


def get_secret_key() -> str:
    return _secret_key
