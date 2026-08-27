"""Media plugins : audio, TTS, musique, lipsync, sous-titres."""

from deepblender.plugins.media.audio import AudioPlugin
from deepblender.plugins.media.tts import TTSPlugin
from deepblender.plugins.media.music import MusicPlugin
from deepblender.plugins.media.lipsync import LipSyncPlugin
from deepblender.plugins.media.subtitle import SubtitleEntry, SubtitlePlugin

__all__ = [
    "AudioPlugin", "TTSPlugin", "MusicPlugin", "LipSyncPlugin",
    "SubtitlePlugin", "SubtitleEntry",
]
