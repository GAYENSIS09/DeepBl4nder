"""Frontière isolée : exécution d'un processus Blender headless.

Ce module est la frontière de confinement (Roadmap C §14) : le code généré et
validé est exécuté dans un sous-processus Blender dédié, jamais in-process.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProcessResult:
    """Résultat d'un processus isolé : code retour, logs, durée."""

    returncode: int
    stdout: str
    stderr: str
    elapsed: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class WorkerCommand:
    """Commande à exécuter dans la frontière isolée."""

    argv: list[str]
    timeout: float = 120.0
    env: dict[str, str] = field(default_factory=dict)


class WorkerProcess:
    """Exécute une commande dans un sous-processus avec timeout et capture des logs."""

    def run(self, command: WorkerCommand, cwd: Path | None = None) -> ProcessResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                command.argv,
                capture_output=True,
                text=True,
                timeout=command.timeout,
                cwd=cwd,
                env=command.env or None,
            )
            return ProcessResult(proc.returncode, proc.stdout, proc.stderr, time.monotonic() - start)
        except subprocess.TimeoutExpired as exc:
            stdout = _coerce_output(exc.stdout)
            stderr = _coerce_output(exc.stderr)
            return ProcessResult(
                returncode=-1,
                stdout=stdout,
                stderr=stderr + f"\n[TIMEOUT after {command.timeout}s]",
                elapsed=time.monotonic() - start,
            )
        except FileNotFoundError as exc:
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=f"executable not found: {exc}",
                elapsed=time.monotonic() - start,
            )


def _coerce_output(output: object) -> str:
    """Normalise stdout/stderr d'un TimeoutExpired (str ou bytes)."""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    if isinstance(output, str):
        return output
    return ""


def blender_version() -> str:
    """Renvoie la version Blender si `bpy` est importable.

    `bpy` n'est disponible que dans l'interpréteur Python embarqué de Blender ;
    l'import est gardé par un try/except pour que ce module fonctionne aussi
    sur un hôte sans Blender.
    """
    try:
        import bpy  # type: ignore[import-not-found]
    except ImportError:
        return "bpy unavailable (Blender non installé sur cet hôte)"
    return bpy.app.version_string
