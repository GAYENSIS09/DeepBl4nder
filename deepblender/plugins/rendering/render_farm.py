"""RenderFarmPlugin : soumission des rendus sur le pool de workers."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from DeepBl4nder.bridges.blender.scheduler import WorkerScheduler
from DeepBl4nder.bridges.blender.bridge import BlenderBridge
from DeepBl4nder.bridge.worker import ProcessResult
from DeepBl4nder.domain.scene import BlenderScript
from DeepBl4nder.plugins.base import Plugin

if TYPE_CHECKING:
    from DeepBl4nder.plugins.rendering.blender import BlenderPlugin
    from DeepBl4nder.plugins.registry import PluginRegistry


@dataclass
class RenderFarmPlugin(Plugin):
    """Distribue les rendus sur le pool (CPU/GPU), un worker par scène.

    Reçoit un PluginRegistry pour partager BlenderPlugin/WorkerScheduler.
    """

    name: str = "render-farm"
    description: str = "Soumission et répartition des rendus sur le pool de workers."
    plugins: "PluginRegistry | None" = field(default=None)
    _scheduler: WorkerScheduler | None = field(default=None, repr=False)

    def available(self) -> bool:
        scheduler = self._get_scheduler()
        return scheduler.worker_count >= 1

    def _get_scheduler(self) -> WorkerScheduler:
        if self._scheduler is None:
            self._scheduler = WorkerScheduler()
        return self._scheduler

    def _get_bridge(self) -> BlenderBridge:
        if self.plugins is None:
            from DeepBl4nder.plugins.registry import PluginRegistry
            self.plugins = PluginRegistry()
        return cast("BlenderPlugin", self.plugins.get("blender")).bridge

    def submit(self, script: BlenderScript, workdir: Path) -> Future[ProcessResult]:
        return self._get_scheduler().submit(lambda: self._get_bridge().run_script(script, workdir))

    def worker_count(self) -> int:
        return self._get_scheduler().worker_count

    def gpu_count(self) -> int:
        return self._get_scheduler().gpu_count

    def add_workers(self, count: int, kind: str = "cpu") -> None:
        self._get_scheduler().add_workers(count, kind=kind)
