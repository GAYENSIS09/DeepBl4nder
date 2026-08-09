"""Registry et versioning des artifacts de production."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4

ArtifactStatus = Literal["spec", "generated", "validated", "executed", "created", "inspect", "approved", "published"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class Artifact:
    """Unité de production persistante, versionnée et adressée par hash."""

    type: str
    name: str
    path: Path
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    version: int = 1
    sha256: str = ""
    status: ArtifactStatus = "generated"
    parents: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    cost: float = 0.0

    def compute_hash(self) -> str:
        self.sha256 = sha256_of(self.path)
        return self.sha256


class ArtifactRegistry:
    """Enregistre les artifacts, gère le versioning par (type, nom) et les statuts."""

    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}
        self._versions: dict[tuple[str, str], int] = {}

    def register(self, artifact: Artifact) -> Artifact:
        """Enregistre un artifact ; incrémente la version si (type, nom) existe déjà."""
        key = (artifact.type, artifact.name)
        self._versions[key] = self._versions.get(key, 0) + 1
        artifact.version = self._versions[key]
        if artifact.path.is_file():
            artifact.compute_hash()
        self._artifacts[artifact.id] = artifact
        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        return self._artifacts.get(artifact_id)

    def latest(self, artifact_type: str, name: str) -> Artifact | None:
        candidates = [
            a for a in self._artifacts.values() if a.type == artifact_type and a.name == name
        ]
        return max(candidates, key=lambda a: a.version) if candidates else None

    def versions(self, artifact_type: str, name: str) -> list[Artifact]:
        return sorted(
            (a for a in self._artifacts.values() if a.type == artifact_type and a.name == name),
            key=lambda a: a.version,
        )

    def set_status(self, artifact_id: str, status: ArtifactStatus) -> Artifact | None:
        artifact = self._artifacts.get(artifact_id)
        if artifact is not None:
            artifact.status = status
        return artifact
