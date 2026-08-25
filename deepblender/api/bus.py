"""Bus d'événements asynchrone pour le temps réel de l'API SaaS (SSE).

Chaque événement porte un ``seq`` global croissant (rôle de ``Last-Event-ID``).
Un abonné reçoit d'abord l'historique borné (rejeu après reconnexion), filtré
par production et par position, puis le flux live. ``publish_nowait`` permet
aux hooks synchrones du pipeline (exécutés dans la boucle d'événements) de
publier sans bloquer.
"""

from __future__ import annotations

import asyncio
from typing import Any


class AsyncEventBus:
    """Pub/sub mémoire pour le SSE : historique borné + flux live."""

    def __init__(self, history_size: int = 500) -> None:
        self._queues: list[tuple[asyncio.Queue[dict[str, Any]], str | None]] = []
        self._history: list[dict[str, Any]] = []
        self._history_size = history_size
        self._seq = 0

    async def subscribe(
        self,
        production_id: str | None = None,
        after: int | None = None,
    ) -> asyncio.Queue[dict[str, Any]]:
        """Abonne un client et remplit sa file avec l'historique pertinent."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        for event in self._history:
            if production_id is not None and event.get("production_id") != production_id:
                continue
            if after is not None and event.get("seq", 0) <= after:
                continue
            queue.put_nowait(event)
        self._queues.append((queue, production_id))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._queues = [(q, pid) for q, pid in self._queues if q is not queue]

    def publish_nowait(self, event: dict[str, Any]) -> None:
        self._seq += 1
        event = {**event, "seq": self._seq}
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history[:] = self._history[-self._history_size :]
        event_pid = event.get("production_id")
        for queue, sub_pid in self._queues:
            if sub_pid is not None and event_pid is not None and sub_pid != event_pid:
                continue
            queue.put_nowait(event)

    async def publish(self, event: dict[str, Any]) -> None:
        self.publish_nowait(event)
