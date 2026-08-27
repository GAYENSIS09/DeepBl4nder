"""Scheduler de workers : pool extensible à chaud, CPU et GPU, 1 worker/scène.

Le scheduler appartient à DeepBlender (Roadmap C §13/§29). Le pool démarre
avec un nombre de workers configurable et accepte l'ajout de workers **sans
redémarrage** via `add_workers` (contrat ADD : « l'ajout d'un worker se fait
sans redémarrage »). Chaque worker porte un `worker_id` et une ressource
(`cpu`/`gpu`) pour le render farm et la corrélation des coûts.
"""

from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class WorkerInfo:
    """Métadonnée d'un worker du pool (corrélation, coûts, logs)."""

    id: str
    kind: str
    created_at: float = field(default_factory=time.time)


class WorkerScheduler:
    """Soumet des tâches à un pool de workers extensible sans redémarrage."""

    def __init__(self, workers: int = 3, gpu_workers: int = 0) -> None:
        if workers < 1:
            raise ValueError("at least one worker is required")
        if gpu_workers < 0:
            raise ValueError("gpu_workers must be >= 0")
        self._tasks: queue.Queue[Callable[[], None]] = queue.Queue()
        self._threads: set[threading.Thread] = set()
        self._workers: dict[str, WorkerInfo] = {}
        self._lock = threading.Lock()
        self._shutdown = False
        for _ in range(workers):
            self._spawn("cpu")
        for _ in range(gpu_workers):
            self._spawn("gpu")

    def _spawn(self, kind: str) -> WorkerInfo:
        info = WorkerInfo(id=uuid.uuid4().hex[:8], kind=kind)
        thread = threading.Thread(target=self._run_loop, name=f"deepblender-{kind}-worker", daemon=True)
        thread.start()
        with self._lock:
            self._threads.add(thread)
            self._workers[info.id] = info
        return info

    def _run_loop(self) -> None:
        while not self._shutdown:
            try:
                task = self._tasks.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                task()
            finally:
                self._tasks.task_done()

    @property
    def worker_count(self) -> int:
        with self._lock:
            return len(self._workers)

    @property
    def gpu_count(self) -> int:
        with self._lock:
            return sum(1 for worker in self._workers.values() if worker.kind == "gpu")

    def workers(self) -> list[WorkerInfo]:
        with self._lock:
            return sorted(self._workers.values(), key=lambda worker: worker.id)

    def add_workers(self, count: int, kind: str = "cpu") -> None:
        """Ajoute `count` workers au pool sans redémarrage (contrat ADD)."""
        if count < 1:
            raise ValueError("count must be >= 1")
        if kind not in ("cpu", "gpu"):
            raise ValueError("kind must be 'cpu' or 'gpu'")
        for _ in range(count):
            self._spawn(kind)

    def submit(self, task: Callable[[], T]) -> Future[T]:
        future: Future[T] = Future()
        self._tasks.put(lambda: self._complete(future, task))
        return future

    def _complete(self, future: Future[T], task: Callable[[], T]) -> None:
        try:
            future.set_result(task())
        except BaseException as exc:  # noqa: BLE001 — propagé via le Future
            future.set_exception(exc)

    def shutdown(self) -> None:
        self._shutdown = True
        with self._lock:
            threads = list(self._threads)
        for thread in threads:
            thread.join(timeout=5)


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée `python -m deepblender.bridges.blender.scheduler`.

    Démarre le pool de workers (CPU/GPU) et maintient le statut en boucle.
    Les jobs sont soumis programmatiquement via `WorkerScheduler.submit`.
    """
    import argparse
    import signal
    import time

    parser = argparse.ArgumentParser(prog="deepblender.bridges.blender.scheduler", description="Coordinateur de render farm (pool de workers).")
    parser.add_argument("--workers", type=int, default=int(os.environ.get("DEEPBLENDER_WORKERS", "3")))
    parser.add_argument("--gpu-workers", type=int, default=int(os.environ.get("DEEPBLENDER_GPU_WORKERS", "0")))
    args = parser.parse_args(argv)

    scheduler = WorkerScheduler(workers=args.workers, gpu_workers=args.gpu_workers)
    print(f"DeepBlender scheduler : {scheduler.worker_count} workers (gpu: {scheduler.gpu_count})")

    def _stop(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _stop)
    try:
        while True:
            time.sleep(5)
            print(f"workers: {scheduler.worker_count} (gpu: {scheduler.gpu_count})", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown()
        print("Scheduler stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
