"""Événements de production : journal persistant (JSONL) et reprise.

La fiabilité DeepBlender repose sur un journal append-only : chaque
transition d'étape est persistée avant d'être appliquée. Après un crash,
`ProductionRun.recover` rejoue le journal et resoumet les étapes démarrées
mais jamais terminées (événements non consommés) — ADD, objectif « reprise
par rejeu des événements non consommés ».

Le module abrite aussi `EventBus`, bus pub/sub mémoire utilisé par la
gateway pour l'observabilité temps réel (SSE, alerte budget < 30 s).
"""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

STEP_EVENTS = ("step_started", "step_completed", "step_failed")
RUN_EVENTS = ("run_started", "run_completed", "run_blocked")
APPROVAL_EVENTS = ("approval_requested", "approval_granted", "approval_rejected")


@dataclass(frozen=True)
class ProductionEvent:
    """Un événement persisté du journal (rejeu et reprise)."""

    seq: int
    kind: str
    ts: float
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


@dataclass
class EventLog:
    """Journal append-only : chaque événement est flush'é avant retour."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cached_last_seq: int | None = None

    def append(self, kind: str, payload: dict[str, Any] | None = None) -> ProductionEvent:
        seq = self._last_seq() + 1
        event = ProductionEvent(seq=seq, kind=kind, ts=time.time(), payload=payload or {})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.to_json() + "\n")
            handle.flush()
        self._cached_last_seq = seq
        return event

    def load(self) -> list[ProductionEvent]:
        if not self.path.exists():
            return []
        events: list[ProductionEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                events.append(ProductionEvent(**data))
        return events

    def _last_seq(self) -> int:
        if self._cached_last_seq is not None:
            return self._cached_last_seq
        seq = 0
        for event in self.load():
            seq = max(seq, event.seq)
        self._cached_last_seq = seq
        return seq

    def last_seq(self) -> int:
        return self._last_seq()


class EventBus:
    """Bus pub/sub mémoire pour l'observabilité temps réel (SSE gateway)."""

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue()
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)
