"""AssetLibraryPlugin : catalogue local des assets (index JSON)."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepblender.plugins.base import Plugin, PluginError


@dataclass
class AssetLibraryPlugin(Plugin):
    """Enregistre, cherche et importe des assets avec hash de provenance."""

    name: str = "asset-library"
    description: str = "Catalogue local des assets (index JSON)."
    index_path: Path = field(default_factory=lambda: Path.cwd() / "asset-library" / "index.json")

    def __post_init__(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write([])

    def available(self) -> bool:
        return True

    def _read(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, entries: list[dict[str, Any]]) -> None:
        self.index_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    def register(self, path: Path, asset_type: str, tags: list[str] | None = None) -> dict[str, Any]:
        if not path.is_file():
            raise PluginError(f"asset file not found: {path}")
        asset_id = uuid.uuid4().hex[:10]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entry = {
            "id": asset_id,
            "type": asset_type,
            "tags": tags or [],
            "path": str(path),
            "hash": digest,
            "registered_at": time.time(),
        }
        entries = self._read()
        entries.append(entry)
        self._write(entries)
        return entry

    def find(self, query: str = "") -> list[dict[str, Any]]:
        needle = query.lower()
        if not needle:
            return self._read()
        return [
            entry
            for entry in self._read()
            if needle in entry.get("type", "").lower()
            or needle in " ".join(entry.get("tags", [])).lower()
            or needle in entry.get("path", "").lower()
        ]

    def import_into(self, asset_id: str, destination: Path) -> Path:
        entry = next((item for item in self._read() if item.get("id") == asset_id), None)
        if entry is None:
            raise PluginError(f"asset not found: {asset_id}")
        source = Path(entry["path"])
        if not source.is_file():
            raise PluginError(f"asset source missing: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination
