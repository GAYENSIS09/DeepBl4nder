"""Tools : primitives d'action importantes (doc 06).

Pas de micro-tools (`move_object`, `rotate_object`…) : ces actions résultent
du Python / Code-as-Action généré. La liste canonique des 8 tools importants
est branchée sur les plugins (Blender, audio, ffmpeg) via PluginRegistry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, cast

from deepblender.plugins.media.audio import AudioPlugin
from deepblender.plugins.rendering.blender import BlenderPlugin
from deepblender.plugins.rendering.ffmpeg import FFmpegPlugin
from deepblender.plugins.registry import PluginRegistry


@dataclass(frozen=True)
class Tool:
    """Primitive d'action importante, liée à une opération de plugin."""

    name: str
    description: str
    run: Callable[..., Any]

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self.run(*args, **kwargs)


@dataclass
class ToolRegistry:
    """Catalogue des tools importants (doc 06, liste canonique).

    Utilise un PluginRegistry partagé pour éviter les doublons d'instances.
    """

    plugins: PluginRegistry = field(default_factory=PluginRegistry)

    def tools(self) -> list[Tool]:
        blender = cast(BlenderPlugin, self.plugins.get("blender"))
        audio = cast(AudioPlugin, self.plugins.get("audio"))
        ffmpeg = cast(FFmpegPlugin, self.plugins.get("ffmpeg"))
        return [
            Tool("inspect_scene", "Inspecte les objets de la scène Blender.", blender.inspect_scene),
            Tool("load_asset", "Append un asset dans la scène Blender.", blender.load_asset),
            Tool("save_blend", "Sauvegarde la scène Blender.", blender.save_scene),
            Tool("render", "Lance un rendu de la scène Blender.", blender.render),
            Tool("inspect_render", "Vérifie un rendu produit (image / QA).", blender.inspect_render),
            Tool("create_audio", "Génère une piste audio (ambiance / ton).", audio.generate_ambience),
            Tool("compose", "Assemble une vidéo et une piste audio (mux).", ffmpeg.mux),
            Tool("export", "Transcode la séquence vers un codec cible.", ffmpeg.transcode),
        ]

    def names(self) -> list[str]:
        return [tool.name for tool in self.tools()]

    def get(self, name: str) -> Tool:
        for tool in self.tools():
            if tool.name == name:
                return tool
        raise KeyError(f"tool not found: {name}")
