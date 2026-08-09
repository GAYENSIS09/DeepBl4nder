"""GitPlugin : versionning de la production (git)."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from deepblender.bridge.worker import WorkerCommand, WorkerProcess
from deepblender.plugins.base import Plugin, PluginError


@dataclass
class GitPlugin(Plugin):
    """Frontière d'intégration git (versionning des artifacts et specs)."""

    name: str = "git"
    description: str = "Versionning de la production (git)."
    git_exe: str | None = None

    def __post_init__(self) -> None:
        self._exe = self.git_exe or os.environ.get("GIT_EXE", "git")
        self._worker = WorkerProcess()

    def available(self) -> bool:
        return shutil.which(self._exe) is not None

    def _run(self, repo: Path, *args: str) -> str:
        if not self.available():
            raise PluginError("git not available (set GIT_EXE or install git)")
        result = self._worker.run(WorkerCommand(argv=[self._exe, *args]), cwd=repo)
        if not result.ok:
            raise PluginError(result.stderr or "git failed")
        return result.stdout

    def commit(self, repo: Path, message: str) -> str:
        self._run(repo, "add", "-A")
        return self._run(repo, "commit", "-m", message)

    def tag(self, repo: Path, name: str) -> str:
        return self._run(repo, "tag", name)

    def status(self, repo: Path) -> str:
        return self._run(repo, "status", "--short")

    def head(self, repo: Path) -> str:
        return self._run(repo, "rev-parse", "--short", "HEAD").strip()
