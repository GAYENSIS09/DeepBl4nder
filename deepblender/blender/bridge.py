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


def _find_blender() -> str | None:
    """Résout le binaire Blender : env explicite, PATH, puis emplacements Windows.

    ``BLENDER_EXE`` prime (chemin absolu ou nom résolvable via PATH). Si rien
    n'est trouvé, on cherche dans les dossiers d'installation Blender
    (``C:\\Program Files\\Blender Foundation\\Blender *\\blender.exe``).
    """
    explicit = (os.environ.get("BLENDER_EXE") or "").strip()
    if explicit:
        if Path(explicit).is_file() or shutil.which(explicit) is not None:
            return explicit
    if shutil.which("blender") is not None:
        return "blender"
    if os.name != "nt":
        return None
    root = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Blender Foundation"
    if not root.is_dir():
        return None
    candidates: list[Path] = [root / "blender.exe"]
    candidates.extend(sorted(root.glob("Blender */blender.exe"), reverse=True))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


@dataclass
class BlenderBridge:
    """Frontière Blender : valide puis exécute des scripts headless."""

    blender_exe: str | None = None
    timeout: float = 300.0

    def __post_init__(self) -> None:
        self._blender_exe = self.blender_exe or _find_blender()
        self._worker = WorkerProcess()

    def available(self) -> bool:
        exe = self._blender_exe
        if not exe:
            return False
        return shutil.which(exe) is not None or Path(exe).is_file()

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
                "Blender executable not found. Install Blender or set "
                "BLENDER_EXE to the full path of blender.exe (see Dockerfile)."
            )
        workdir.mkdir(parents=True, exist_ok=True)
        script_path = workdir / f"{script.scene_name}_v{script.version}.py"
        script_path.write_text(script.code, encoding="utf-8")
        command = WorkerCommand(
            argv=[self._blender_exe, "-b", "-P", str(script_path)],
            timeout=self.timeout,
        )
        return self._worker.run(command, cwd=workdir)
