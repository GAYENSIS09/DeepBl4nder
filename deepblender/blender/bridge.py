"""BlenderBridge : lance Blender headless sur un script bpy validé.

Le bridge exécute `blender -b -P <script>` dans un sous-processus via la
frontière isolée (`deepblender.bridge.worker`). `BLENDER_EXE` permet de
surcharger le binaire (ADR-009, Dockerfile).

Sécurité (fail-closed) : aucun script n'est exécuté sans avoir passé le
validateur AST (`CodePolicyViolation` sinon) — ADD, objectif « aucun code
généré ne s'exécute en dehors du périmètre autorisé ».
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from deepblender.bridge.worker import ProcessResult, WorkerCommand, WorkerProcess
from deepblender.codegen import CodePolicyViolation, validate_for_worker
from deepblender.domain.scene import BlenderScript


class BlenderNotFoundError(RuntimeError):
    """Blender n'est pas disponible sur cet hôte (binaire introuvable)."""


@dataclass
class BlenderBridge:
    """Frontière Blender : valide puis exécute des scripts headless."""

    blender_exe: str | None = None
    timeout: float = 300.0

    def __post_init__(self) -> None:
        self._blender_exe = self.blender_exe or os.environ.get("BLENDER_EXE", "blender")
        self._worker = WorkerProcess()

    def available(self) -> bool:
        return shutil.which(self._blender_exe) is not None

    def run_script(self, script: BlenderScript, workdir: Path) -> ProcessResult:
        """Valide le script (fail-closed), puis l'exécute dans Blender headless."""
        report = validate_for_worker(script.code)
        if not report.ok:
            raise CodePolicyViolation(
                f"Script '{script.scene_name}' rejected by code policy: "
                f"{'; '.join(report.errors)}"
            )
        if not self.available():
            raise BlenderNotFoundError(
                f"Blender executable not found: '{self._blender_exe}'. "
                "Set BLENDER_EXE or install Blender (see Dockerfile)."
            )
        workdir.mkdir(parents=True, exist_ok=True)
        script_path = workdir / f"{script.scene_name}_v{script.version}.py"
        script_path.write_text(script.code, encoding="utf-8")
        command = WorkerCommand(
            argv=[self._blender_exe, "-b", "-P", str(script_path)],
            timeout=self.timeout,
        )
        return self._worker.run(command, cwd=workdir)
