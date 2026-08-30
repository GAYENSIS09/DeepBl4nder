"""Registry de plugins : découverte et accès aux frontières externes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from DeepBl4nder.plugins.base import Plugin
from DeepBl4nder.plugins.knowledge.asset_library import AssetLibraryPlugin
from DeepBl4nder.plugins.media.audio import AudioPlugin
from DeepBl4nder.plugins.media.subtitle import SubtitlePlugin
from DeepBl4nder.plugins.media.tts import TTSPlugin
from DeepBl4nder.plugins.rendering.blender import BlenderPlugin
from DeepBl4nder.plugins.rendering.ffmpeg import FFmpegPlugin
from DeepBl4nder.plugins.rendering.render_farm import RenderFarmPlugin
from DeepBl4nder.plugins.knowledge.knowledge_graph import KnowledgeGraphPlugin
from DeepBl4nder.plugins.storage.storage import StoragePlugin
from DeepBl4nder.plugins.storage.git import GitPlugin

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
    on_plugin: Callable[[str, str], None] | None = field(default=None)

    def __post_init__(self) -> None:
        for name, plugin_cls in _BUILTINS.items():
            if name == "render-farm":
                self.plugins[name] = RenderFarmPlugin(plugins=self)
            else:
                self.plugins[name] = plugin_cls()

    def record(self, name: str, method: str) -> None:
        """Signale un usage de plugin (observabilité, jamais bloquant)."""
        if self.on_plugin is not None:
            self.on_plugin(name, method)

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
