"""Scheduler de workers : soumission et ajout de workers à chaud."""

from __future__ import annotations

import time

import pytest

from deepblender.blender.scheduler import WorkerScheduler


def test_submit_returns_result() -> None:
    scheduler = WorkerScheduler(workers=2)
    future = scheduler.submit(lambda: 42)
    assert future.result(timeout=5) == 42
    scheduler.shutdown()


def test_submit_propagates_exception() -> None:
    scheduler = WorkerScheduler(workers=1)

    def fail() -> None:
        raise ValueError("boom")

    future = scheduler.submit(fail)
    with pytest.raises(ValueError):
        future.result(timeout=5)
    scheduler.shutdown()


def test_add_workers_scales_without_restart() -> None:
    scheduler = WorkerScheduler(workers=1)
    initial = scheduler.worker_count
    scheduler.add_workers(2)
    assert scheduler.worker_count == initial + 2
    futures = [scheduler.submit(lambda i=i: i) for i in range(5)]
    assert sorted(f.result(timeout=5) for f in futures) == [0, 1, 2, 3, 4]
    scheduler.shutdown()


def test_add_workers_rejects_invalid_count() -> None:
    scheduler = WorkerScheduler(workers=1)
    with pytest.raises(ValueError):
        scheduler.add_workers(0)
    scheduler.shutdown()


def test_workers_run_in_parallel() -> None:
    scheduler = WorkerScheduler(workers=3)
    started_at = time.monotonic()

    def slow() -> None:
        time.sleep(0.4)
        return None

    futures = [scheduler.submit(slow) for _ in range(3)]
    for future in futures:
        future.result(timeout=10)
    elapsed = time.monotonic() - started_at
    scheduler.shutdown()
    assert elapsed < 1.0
