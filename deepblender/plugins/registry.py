"""Registry de plugins : découverte et accès aux frontières externes."""

from __future__ import annotations

from dataclasses import dataclass, field

from deepblender.plugins.asset_library import AssetLibraryPlugin
from deepblender.plugins.audio import AudioPlugin
from deepblender.plugins.base import Plugin
from deepblender.plugins.blender import BlenderPlugin
from deepblender.plugins.ffmpeg import FFmpegPlugin
from deepblender.plugins.git import GitPlugin
from deepblender.plugins.knowledge_graph import KnowledgeGraphPlugin
from deepblender.plugins.render_farm import RenderFarmPlugin
from deepblender.plugins.storage import StoragePlugin
from deepblender.plugins.subtitle import SubtitlePlugin
from deepblender.plugins.tts import TTSPlugin

_BUILTINS: dict[str, type[Plugin]] = {
    "blender": BlenderPlugin,
    "ffmpeg": FFmpegPlugin,
    "audio": AudioPlugin,
    "tts": TTSPlugin,
    "storage": StoragePlugin,
    "asset-library": AssetLibraryPlugin,
    "subtitle": SubtitlePlugin,
    "git": GitPlugin,
    "knowledge-graph": KnowledgeGraphPlugin,
    "render-farm": RenderFarmPlugin,
}


@dataclass
class PluginRegistry:
    """Enregistre les plugins (frontières externes) et les expose."""

    plugins: dict[str, Plugin] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, plugin_cls in _BUILTINS.items():
            if name == "render-farm":
                self.plugins[name] = plugin_cls(plugins=self)
            else:
                self.plugins[name] = plugin_cls()

    def register(self, plugin: Plugin) -> None:
        if not plugin.name:
            raise ValueError("plugin name is required")
        self.plugins[plugin.name] = plugin

    def get(self, name: str) -> Plugin:
        try:
            return self.plugins[name]
        except KeyError:
            raise KeyError(f"plugin not found: {name}") from None

    def get_or_create(self, name: str) -> Plugin:
        """Alias pour compatibilité : les plugins sont déjà instanciés."""
        return self.get(name)

    def all_plugins(self) -> list[Plugin]:
        return list(self.plugins.values())

    def discover(self) -> list[dict[str, object]]:
        return [plugin.info() for plugin in self.all_plugins()]

    def available(self) -> list[str]:
        return [plugin.name for plugin in self.all_plugins() if plugin.available()]
