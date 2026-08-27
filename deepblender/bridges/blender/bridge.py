"""BlenderBridge : lance Blender headless sur un script bpy validé.

Le bridge exécute `blender -b -P <script>` dans un sous-processus via la
frontière isolée (`DeepBl4nder.bridge.worker`). `BLENDER_EXE` permet de
surcharger le binaire (ADR-009, Dockerfile).

Sécurité (fail-closed) : aucun script n'est exécuté sans avoir passé le
validateur AST (`CodePolicyViolation` sinon) — ADD, objectif « aucun code
généré ne s'exécute en dehors du périmètre autorisé ».

GPU : détecte CUDA/OptiX automatiquement pour un rendu plus rapide.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from DeepBl4nder.bridge.worker import ProcessResult, WorkerCommand, WorkerProcess
from DeepBl4nder.codegen import CodePolicyViolation, validate_for_worker
from DeepBl4nder.domain.scene import BlenderScript


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


def _detect_gpu_backend() -> str | None:
    """Détecte le backend GPU disponible pour Blender (CUDA, OPTIX, HIP, METAL)."""
    # Check via nvidia-smi (CUDA/OptiX)
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Check for OptiX support via Blender
            return "OPTIX"  # Prefer OptiX over CUDA if available
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check via ROCm (HIP) on Linux
    if os.name != "nt":
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return "HIP"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # macOS Metal
    if os.name == "nt":
        return None  # No Metal on Windows
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True, text=True, timeout=5,
        )
        if "Apple" in result.stdout:
            return "METAL"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


@dataclass
class BlenderBridge:
    """Frontière Blender : valide puis exécute des scripts headless."""

    blender_exe: str | None = None
    timeout: float = 600.0  # Increased for production renders (256+ samples)
    prefer_gpu: bool = True
    _gpu_backend: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._blender_exe = self.blender_exe or _find_blender()
        self._worker = WorkerProcess()
        self._gpu_backend = _detect_gpu_backend() if self.prefer_gpu else None

    def available(self) -> bool:
        exe = self._blender_exe
        if not exe:
            return False
        return shutil.which(exe) is not None or Path(exe).is_file()

    def get_gpu_backend(self) -> str | None:
        """Retourne le backend GPU détecté (CUDA, OPTIX, HIP, METAL) ou None."""
        return self._gpu_backend

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

        # Build Blender command with GPU preferences
        argv = [self._blender_exe, "-b", "-P", str(script_path)]

        # Add GPU backend override via environment
        env = os.environ.copy()
        if self._gpu_backend:
            # Blender 4.x: cycles_device is set in script, but we can hint via env
            if self._gpu_backend == "OPTIX":
                env["CYCLES_OPTIX"] = "1"
            elif self._gpu_backend == "CUDA":
                env["CYCLES_CUDA"] = "1"

        command = WorkerCommand(
            argv=argv,
            timeout=self.timeout,
        )
        return self._worker.run(command, cwd=workdir)
