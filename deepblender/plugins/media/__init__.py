"""Media plugins : audio, TTS, sous-titres."""

from deepblender.plugins.media.audio import AudioPlugin
from deepblender.plugins.media.tts import TTSPlugin
from deepblender.plugins.media.subtitle import SubtitleEntry, SubtitlePlugin

__all__ = ["AudioPlugin", "TTSPlugin", "SubtitlePlugin", "SubtitleEntry"]
