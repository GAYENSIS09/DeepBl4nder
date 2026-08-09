"""Plugins (frontières externes) et tools (primitives d'action).

Ne contient AUCUN runtime agentique : les plugins sont des passerelles vers
des systèmes externes (Blender, FFmpeg, TTS, storage, git…), utilisés par les
agents NOOA (doc 06-tools-et-plugins.md).
"""

from __future__ import annotations

from deepblender.plugins.asset_library import AssetLibraryPlugin
from deepblender.plugins.audio import AudioPlugin
from deepblender.plugins.base import Plugin, PluginError
from deepblender.plugins.blender import BlenderPlugin
from deepblender.plugins.ffmpeg import FFmpegPlugin
from deepblender.plugins.git import GitPlugin
from deepblender.plugins.knowledge_graph import KnowledgeGraphPlugin
from deepblender.plugins.registry import PluginRegistry
from deepblender.plugins.render_farm import RenderFarmPlugin
from deepblender.plugins.storage import StoragePlugin
from deepblender.plugins.subtitle import SubtitleEntry, SubtitlePlugin
from deepblender.plugins.tools import Tool, ToolRegistry
from deepblender.plugins.tts import TTSPlugin

__all__ = [
    "AssetLibraryPlugin",
    "AudioPlugin",
    "BlenderPlugin",
    "FFmpegPlugin",
    "GitPlugin",
    "KnowledgeGraphPlugin",
    "Plugin",
    "PluginError",
    "PluginRegistry",
    "RenderFarmPlugin",
    "StoragePlugin",
    "SubtitleEntry",
    "SubtitlePlugin",
    "TTSPlugin",
    "Tool",
    "ToolRegistry",
]
