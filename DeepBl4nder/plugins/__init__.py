"""Plugins DeepBl4nder : architecture modulaire par domaine.

Structure :
├── base.py              # Classe de base Plugin
├── registry.py          # PluginRegistry (registre central)
├── tools.py             # ToolRegistry (outils LLM)
│
├── media/               # Plugins média
│   ├── audio.py         # AudioPlugin (génération audio)
│   ├── tts.py           # TTSPlugin (text-to-speech)
│   └── subtitle.py      # SubtitlePlugin (sous-titres)
│
├── rendering/           # Plugins rendu
│   ├── blender.py       # BlenderPlugin (Blender)
│   ├── ffmpeg.py        # FFmpegPlugin (FFmpeg)
│   └── render_farm.py   # RenderFarmPlugin (ferme de rendu)
│
├── storage/             # Plugins stockage
│   ├── storage.py       # StoragePlugin
│   └── git.py           # GitPlugin
│
└── knowledge/           # Plugins connaissance
    ├── knowledge_graph.py  # KnowledgeGraphPlugin
    └── asset_library.py    # AssetLibraryPlugin
"""

from DeepBl4nder.plugins.base import Plugin, PluginError
from DeepBl4nder.plugins.registry import PluginRegistry
from DeepBl4nder.plugins.tools import Tool, ToolRegistry

# Media
from DeepBl4nder.plugins.media import AudioPlugin, TTSPlugin, SubtitlePlugin, SubtitleEntry

# Rendering
from DeepBl4nder.plugins.rendering import BlenderPlugin, FFmpegPlugin, RenderFarmPlugin

# Storage
from DeepBl4nder.plugins.storage import StoragePlugin, GitPlugin

# Knowledge
from DeepBl4nder.plugins.knowledge import KnowledgeGraphPlugin, AssetLibraryPlugin

__all__ = [
    # Base
    "Plugin",
    "PluginError",
    "PluginRegistry",
    "Tool",
    "ToolRegistry",
    # Media
    "AudioPlugin",
    "TTSPlugin",
    "SubtitlePlugin",
    "SubtitleEntry",
    # Rendering
    "BlenderPlugin",
    "FFmpegPlugin",
    "RenderFarmPlugin",
    # Storage
    "StoragePlugin",
    "GitPlugin",
    # Knowledge
    "KnowledgeGraphPlugin",
    "AssetLibraryPlugin",
]
