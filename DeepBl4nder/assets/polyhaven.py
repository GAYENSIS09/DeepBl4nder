"""Client API Poly Haven : HDRIs, textures, modèles 3D CC0.

Fournit des helpers pour télécharger et appliquer des assets Poly Haven
dans des scènes Blender. Les assets sont tous en licence CC0 (public domain).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

POLYHAVEN_API_BASE = "https://api.polyhaven.com"


class PolyHavenClient:
    """Client pour l'API Poly Haven."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir else Path("polyhaven_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "DeepBl4nder/0.2"})

    def search(
        self,
        category: str = "hdris",
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recherche des assets sur Poly Haven."""
        params: dict[str, Any] = {"t": category, "limit": limit}
        if tags:
            params["c"] = ",".join(tags)

        resp = self._session.get(f"{POLYHAVEN_API_BASE}/assets", params=params)
        resp.raise_for_status()
        assets = resp.json()

        return [
            {
                "name": name,
                "category": category,
                "tags": info.get("tags", []),
                "date_published": info.get("date_published"),
            }
            for name, info in list(assets.items())[:limit]
        ]

    def get_files(self, name: str) -> dict[str, Any]:
        """Récupère les fichiers disponibles pour un asset."""
        resp = self._session.get(f"{POLYHAVEN_API_BASE}/files/{name}")
        resp.raise_for_status()
        return resp.json()

    def download(
        self,
        name: str,
        file_type: str = "hdri",
        resolution: str = "1k",
        fmt: str = "exr",
    ) -> Path:
        """Télécharge un fichier d'asset avec cache local."""
        cache_key = f"{name}_{file_type}_{resolution}.{fmt}"
        cache_path = self._cache_dir / cache_key

        if cache_path.exists():
            logger.debug("Cache hit: %s", cache_key)
            return cache_path

        files = self.get_files(name)
        file_data = files.get(file_type, {}).get(resolution, {})
        if isinstance(file_data, dict):
            url = file_data.get(fmt)
        else:
            url = file_data

        if not url:
            raise ValueError(
                f"No {file_type}/{resolution}/{fmt} found for {name}. "
                f"Available: {list(files.get(file_type, {}).keys())}"
            )

        logger.info("Downloading %s → %s", url, cache_path)
        resp = self._session.get(url, stream=True)
        resp.raise_for_status()
        with open(cache_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return cache_path

    def download_hdri(self, name: str, resolution: str = "1k") -> Path:
        """Télécharge un HDRI."""
        return self.download(name, file_type="hdri", resolution=resolution, fmt="exr")

    def download_texture_map(
        self, name: str, map_type: str = "diffuse", resolution: str = "1k"
    ) -> Path:
        """Télécharge une map de texture."""
        return self.download(name, file_type="texture", resolution=resolution, fmt="png")

    def search_hdris(self, tags: list[str] | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Recherche des HDRIs."""
        return self.search("hdris", tags=tags, limit=limit)

    def search_textures(self, tags: list[str] | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Recherche des textures."""
        return self.search("textures", tags=tags, limit=limit)


# Singleton pour usage global
_default_client: PolyHavenClient | None = None


def get_client(cache_dir: str | Path | None = None) -> PolyHavenClient:
    """Retourne le client Poly Haven par défaut."""
    global _default_client
    if _default_client is None:
        _default_client = PolyHavenClient(cache_dir=cache_dir)
    return _default_client
