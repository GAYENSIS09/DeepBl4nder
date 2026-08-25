"""StoragePlugin : frontière de persistance des artifacts (filesystem)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from deepblender.plugins.base import Plugin, PluginError


@dataclass
class StoragePlugin(Plugin):
    """Persiste et récupère les artifacts dans un répertoire racine."""

    name: str = "storage"
    description: str = "Persistance et récupération des artifacts (filesystem)."
    root: Path = field(default_factory=lambda: Path.cwd() / "artifacts")

    def available(self) -> bool:
        return True

    def store(self, artifact: Path, key: str) -> Path:
        destination = (self.root / key).resolve()
        if not str(destination).startswith(str(self.root.resolve())):
            raise PluginError(f"key escapes storage root: {key}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifact, destination)
        return destination

    def retrieve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise PluginError(f"key escapes storage root: {key}")
        if not path.is_file():
            raise PluginError(f"artifact not found: {key}")
        return path

    def keys(self, prefix: str = "") -> list[str]:
        base = self.root / prefix if prefix else self.root
        if not base.is_dir():
            return []
        return sorted(path.relative_to(self.root).as_posix() for path in base.rglob("*") if path.is_file())
