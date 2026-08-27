"""Asset Library : personnages rigged, animations, objets 3D.

Fournit des helpers pour télécharger et intégrer des assets 3D (GLB/FBX)
dans les scènes Blender. Sources : Quaternius (CC0), Mixamo, PolyHaven.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

QUATERNIUS_API = "https://quaternius.com/api"
POLYHAVEN_MODELS_API = "https://api.polyhaven.com/assets"


class CharacterAssetClient:
    """Client pour récupérer des personnages rigged 3D (GLB/FBX)."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir else Path("deepblender_cache/characters")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "DeepBlender/0.3"})

    def search(
        self,
        query: str = "",
        source: str = "quaternius",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recherche des assets de personnages."""
        if source == "quaternius":
            return self._search_quaternius(query, limit)
        elif source == "polyhaven":
            return self._search_polyhaven_models(query, limit)
        return []

    def _search_quaternius(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Recherche sur Quaternius (personnages gratuits CC0)."""
        try:
            resp = self._session.get(f"{QUATERNIUS_API}/packages", timeout=15)
            resp.raise_for_status()
            packages = resp.json()
            results = []
            for pkg in packages:
                name = pkg.get("name", "")
                if query.lower() in name.lower() or not query:
                    results.append({
                        "name": name,
                        "source": "quaternius",
                        "url": pkg.get("download", ""),
                        "tags": pkg.get("tags", []),
                    })
                    if len(results) >= limit:
                        break
            return results
        except Exception as e:
            logger.warning("Quaternius search failed: %s", e)
            return self._fallback_characters(query, limit)

    def _search_polyhaven_models(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Recherche de modèles sur PolyHaven."""
        try:
            params = {"t": "models", "limit": limit}
            if query:
                params["c"] = query
            resp = self._session.get(POLYHAVEN_MODELS_API, params=params, timeout=15)
            resp.raise_for_status()
            assets = resp.json()
            return [
                {
                    "name": name,
                    "source": "polyhaven",
                    "tags": info.get("tags", []),
                }
                for name, info in list(assets.items())[:limit]
            ]
        except Exception as e:
            logger.warning("PolyHaven model search failed: %s", e)
            return []

    def _fallback_characters(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Fallback :assets prédéfinis quand les APIs sont indisponibles."""
        PRESET_CHARACTERS = [
            {"name": "woman_professional", "source": "fallback", "tags": ["woman", "professional", "idle"]},
            {"name": "man_casual", "source": "fallback", "tags": ["man", "casual", "walking"]},
            {"name": "child_school", "source": "fallback", "tags": ["child", "school", "running"]},
            {"name": "elderly_walking", "source": "fallback", "tags": ["elderly", "walking", "cane"]},
            {"name": "robot_friendly", "source": "fallback", "tags": ["robot", "friendly", "idle"]},
            {"name": "creature_wolf", "source": "fallback", "tags": ["animal", "wolf", "quadruped"]},
            {"name": "creature_bird", "source": "fallback", "tags": ["animal", "bird", "flying"]},
            {"name": "character_ninja", "source": "fallback", "tags": ["ninja", "combat", "running"]},
        ]
        if not query:
            return PRESET_CHARACTERS[:limit]
        return [
            c for c in PRESET_CHARACTERS
            if any(query.lower() in t for t in c["tags"])
        ][:limit]

    def download(
        self,
        name: str,
        source: str = "quaternius",
        fmt: str = "glb",
    ) -> Path:
        """Télécharge un asset avec cache local."""
        cache_path = self._cache_dir / f"{source}__{name}.{fmt}"

        if cache_path.exists():
            logger.debug("Cache hit: %s", cache_path.name)
            return cache_path

        if source == "fallback":
            return self._generate_placeholder(name, cache_path)

        try:
            if source == "quaternius":
                url = self._get_quaternius_download_url(name, fmt)
            elif source == "polyhaven":
                url = self._get_polyhaven_download_url(name, fmt)
            else:
                raise ValueError(f"Unknown source: {source}")

            logger.info("Downloading %s -> %s", url, cache_path)
            resp = self._session.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            with open(cache_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return cache_path

        except Exception as e:
            logger.warning("Download failed for %s/%s: %s", source, name, e)
            return self._generate_placeholder(name, cache_path)

    def _get_quaternius_download_url(self, name: str, fmt: str) -> str:
        """Récupère l'URL de téléchargement Quaternius."""
        resp = self._session.get(f"{QUATERNIUS_API}/packages/{name}", timeout=15)
        resp.raise_for_status()
        pkg = resp.json()
        downloads = pkg.get("downloads", {})
        for ext in [fmt, "fbx", "blend", "glb"]:
            if ext in downloads:
                return downloads[ext]
        raise ValueError(f"No {fmt} download for {name}")

    def _get_polyhaven_download_url(self, name: str, fmt: str) -> str:
        """Récupère l'URL de téléchargement PolyHaven."""
        resp = self._session.get(f"https://api.polyhaven.com/files/{name}", timeout=15)
        resp.raise_for_status()
        files = resp.json()
        model_data = files.get(fmt, {})
        if isinstance(model_data, dict):
            for res in ["1k", "2k", "4k"]:
                if res in model_data:
                    return model_data[res]
        raise ValueError(f"No {fmt} files for {name}")

    def _generate_placeholder(self, name: str, path: Path) -> Path:
        """Génère un placeholder minimal (Cube basique) quand le téléchargement échoue."""
        placeholder_code = '''import bpy
import sys

# Placeholder character - basic humanoid cube figure
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Body
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 1.0))
body = bpy.context.active_object
body.name = "PLACEHOLDER_body"
body.scale = (0.3, 0.2, 0.5)

# Head
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0, 0, 1.8))
head = bpy.context.active_object
head.name = "PLACEHOLDER_head"

# Left arm
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0.45, 0, 1.2))
larm = bpy.context.active_object
larm.name = "PLACEHOLDER_larm"
larm.scale = (0.08, 0.08, 0.25)

# Right arm
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(-0.45, 0, 1.2))
rarm = bpy.context.active_object
rarm.name = "PLACEHOLDER_rarm"
rarm.scale = (0.08, 0.08, 0.25)

# Left leg
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0.12, 0, 0.3))
lleg = bpy.context.active_object
lleg.name = "PLACEHOLDER_lleg"
lleg.scale = (0.1, 0.1, 0.3)

# Right leg
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(-0.12, 0, 0.3))
rleg = bpy.context.active_object
rleg.name = "PLACEHOLDER_rleg"
rleg.scale = (0.1, 0.1, 0.3)

# Basic material
mat = bpy.data.materials.new(name="PLACEHOLDER_mat")
mat.diffuse_color = (0.6, 0.6, 0.8, 1.0)
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.data.materials.append(mat)

bpy.ops.wm.save_as_mainfile(filepath=r"''' + str(path.resolve()).replace("\\", "/") + '''")
'''
        placeholder_path = self._cache_dir / f"placeholder_{name}.py"
        placeholder_path.write_text(placeholder_code, encoding="utf-8")
        logger.info("Generated placeholder script: %s", placeholder_path)
        return placeholder_path

    def search_characters(self, query: str = "", limit: int = 10) -> list[dict[str, Any]]:
        """Recherche de personnages avec fallback automatique."""
        results = self.search(query, source="quaternius", limit=limit)
        if not results:
            results = self.search(query, source="polyhaven", limit=limit)
        if not results:
            results = self._fallback_characters(query, limit)
        return results


# Singleton
_default_client: CharacterAssetClient | None = None


def get_character_client(cache_dir: str | Path | None = None) -> CharacterAssetClient:
    """Retourne le client de personnages par défaut."""
    global _default_client
    if _default_client is None:
        _default_client = CharacterAssetClient(cache_dir=cache_dir)
    return _default_client
