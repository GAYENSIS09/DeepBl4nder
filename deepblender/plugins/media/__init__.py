"""Media plugins : audio, TTS, musique, lipsync, sous-titres."""

from DeepBl4nder.plugins.media.audio import AudioPlugin
from DeepBl4nder.plugins.media.tts import TTSPlugin
from DeepBl4nder.plugins.media.music import MusicPlugin
from DeepBl4nder.plugins.media.lipsync import LipSyncPlugin
from DeepBl4nder.plugins.media.subtitle import SubtitleEntry, SubtitlePlugin

__all__ = [
    "AudioPlugin", "TTSPlugin", "MusicPlugin", "LipSyncPlugin",
    "SubtitlePlugin", "SubtitleEntry",
]
