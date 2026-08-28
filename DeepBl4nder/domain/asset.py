"""Objet domaine : Asset (cycle de vie, hash, version)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AssetKind = Literal["character", "prop", "environment", "texture", "hdri", "audio"]


def sha256_of_file(path: Path) -> str:
    """Empreinte SHA-256 d'un fichier (déterministe)."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class Asset:
    """Asset de production, versionné et adressé par hash."""

    name: str
    kind: AssetKind
    path: Path
    version: int = 1
    sha256: str = ""

    def register(self) -> str:
        """Calcule et enregistre le hash de l'asset."""
        self.sha256 = sha256_of_file(self.path)
        return self.sha256
