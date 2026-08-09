"""Plugin : frontière d'intégration avec un système externe.

Un plugin n'est PAS un deuxième runtime agentique : c'est une passerelle
vers un système externe (Blender, FFmpeg, TTS, storage…). Les agents NOOA
restent le runtime ; ils utilisent les plugins via des tools ou du Python
généré (doc 06-tools-et-plugins.md).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PluginError(RuntimeError):
    """Échec d'un plugin ou d'un tool."""


class Plugin(ABC):
    """Interface minimale d'un plugin (frontière externe)."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def available(self) -> bool:
        """Le système externe est-il joignable depuis cet hôte ?"""

    def info(self) -> dict[str, object]:
        return {"name": self.name, "description": self.description, "available": self.available()}
