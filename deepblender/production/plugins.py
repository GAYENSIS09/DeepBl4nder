"""Mixin pour les raccourcis d'accès aux plugins."""

from __future__ import annotations

from typing import Any


class PluginShortcuts:
    """Raccourcis pratiques pour accéder aux plugins par nom."""

    @property
    def audio_plugin(self) -> Any:
        return self.plugins.get("audio")

    @property
    def ffmpeg_plugin(self) -> Any:
        return self.plugins.get("ffmpeg")

    @property
    def subtitle_plugin(self) -> Any:
        return self.plugins.get("subtitle")

    @property
    def tts_plugin(self) -> Any:
        return self.plugins.get("tts")

    @property
    def blender_plugin(self) -> Any:
        return self.plugins.get("blender")

    @property
    def storage_plugin(self) -> Any:
        return self.plugins.get("storage")

    @property
    def git_plugin(self) -> Any:
        return self.plugins.get("git")

    @property
    def knowledge_graph_plugin(self) -> Any:
        return self.plugins.get("knowledge-graph")

    @property
    def asset_library_plugin(self) -> Any:
        return self.plugins.get("asset-library")
