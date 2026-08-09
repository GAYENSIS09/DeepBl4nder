"""BlenderPlugin : frontière d'intégration vers Blender.

Expose les opérations importantes du doc 06 (pas de micro-tools) :
`inspect_scene`, `execute_python`, `render`, `save_scene`, `load_asset`.
Tout script passe par le validateur AST (fail-closed) puis le bridge
(`blender -b -P`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from deepblender.blender.bridge import BlenderBridge
from deepblender.bridge.worker import ProcessResult
from deepblender.domain.scene import BlenderScript
from deepblender.plugins.base import Plugin

_INSPECT_TEMPLATE = (
    "import bpy\n"
    "for obj in bpy.context.scene.objects:\n"
    "    print(obj.name)\n"
)

_RENDER_TEMPLATE = (
    "import bpy\n"
    "scene = bpy.context.scene\n"
    "scene.render.image_settings.file_format = 'PNG'\n"
    "scene.render.filepath = 'render_0001.png'\n"
    "bpy.ops.render.render(write_still=True)\n"
)


@dataclass
class BlenderPlugin(Plugin):
    """Frontière d'intégration Blender (doc 06, exemple canonique)."""

    name: str = "blender"
    description: str = "Inspect, execute, render, save et load sur Blender headless."
    bridge: BlenderBridge = field(default_factory=BlenderBridge)
    workdir: Path = field(default_factory=Path.cwd)

    def available(self) -> bool:
        return self.bridge.available()

    def execute_python(self, script: BlenderScript) -> ProcessResult:
        """Exécute un script bpy généré (validé fail-closed puis lancé)."""
        return self.bridge.run_script(script, self.workdir)

    def inspect_scene(self, scene_name: str = "scene") -> ProcessResult:
        return self.bridge.run_script(BlenderScript(code=_INSPECT_TEMPLATE, scene_name=scene_name), self.workdir)

    def render(self, scene_name: str = "scene") -> ProcessResult:
        return self.bridge.run_script(BlenderScript(code=_RENDER_TEMPLATE, scene_name=scene_name), self.workdir)

    def inspect_render(self, render_path: Path) -> dict[str, object]:
        """Vérifie qu'un rendu a bien été produit (existence, taille)."""
        if not render_path.is_file():
            return {"exists": False, "bytes": 0, "ok": False}
        size = render_path.stat().st_size
        return {"exists": True, "bytes": size, "ok": size > 0}

    def save_scene(self, scene_name: str, path: Path) -> ProcessResult:
        code = f"import bpy\nbpy.ops.wm.save_as_mainfile(filepath={str(path)!r})\n"
        return self.bridge.run_script(BlenderScript(code=code, scene_name=scene_name), self.workdir)

    def load_asset(self, scene_name: str, path: Path) -> ProcessResult:
        code = (
            "import bpy\n"
            f"bpy.ops.wm.append(filepath={str(path)!r}, directory={str(path.parent)!r}, filename={path.name!r})\n"
        )
        return self.bridge.run_script(BlenderScript(code=code, scene_name=scene_name), self.workdir)
