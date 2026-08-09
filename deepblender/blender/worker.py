"""BlenderWorker : worker jetable avec statut, logs et artifacts.

Cible (Roadmap C §13) : worker_id, GPU, scène, processus, environnement,
timeout, statut, artifacts, logs ; 3 workers parallèles, 1 worker/scène,
ajout dynamique sans redémarrage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from deepblender.blender.bridge import BlenderBridge
from deepblender.bridge.worker import ProcessResult
from deepblender.domain.scene import BlenderScript


class WorkerStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class BlenderWorker:
    """Un worker Blender isolé, dédié à une scène."""

    worker_id: str
    workdir: Path
    bridge: BlenderBridge = field(default_factory=BlenderBridge)
    status: WorkerStatus = WorkerStatus.CREATED
    scene_name: str = ""
    logs: list[str] = field(default_factory=list)

    def render(self, script: BlenderScript) -> ProcessResult:
        """Exécute le script validé dans Blender headless."""
        self.scene_name = script.scene_name
        self.status = WorkerStatus.RUNNING
        try:
            result = self.bridge.run_script(script, self.workdir)
        except RuntimeError as exc:
            self.logs.append(str(exc))
            self.status = WorkerStatus.FAILED
            return ProcessResult(-1, "", str(exc), 0.0)
        self.logs.append(result.stdout)
        if result.stderr:
            self.logs.append(result.stderr)
        self.status = WorkerStatus.DONE if result.ok else WorkerStatus.FAILED
        return result
