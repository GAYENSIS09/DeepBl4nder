"""TTSPlugin : integration Bark/CosyVoice pour la synthese vocale.

Genere des pistes vocales a partir de texte avec emotion et langue.
"""

from __future__ import annotations

import logging
import os
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from deepblender.plugins.base import Plugin

logger = logging.getLogger("deepblender.plugins.tts")

_RATE = 24000


@dataclass
class TTSPlugin(Plugin):
    """Synthese vocale via Bark (local) ou fallback deterministe."""

    name: str = "tts"
    description: str = "Synthese vocale : Bark (local), CosyVoice, fallback wave."

    def available(self) -> bool:
        bark_path = os.environ.get("BARK_MODEL_PATH", "")
        cosyvoice_path = os.environ.get("COSYVOICE_MODEL_PATH", "")
        tts_binary = os.environ.get("TTS_BINARY", "")
        return bool(bark_path or cosyvoice_path or tts_binary)

    def generate_voice(
        self,
        text: str,
        out_path: Path,
        language: str = "fr",
        emotion: str = "neutral",
        speaker: str | None = None,
    ) -> Path:
        """Genere un fichier audio WAV a partir de texte."""
        bark_path = os.environ.get("BARK_MODEL_PATH", "")
        if bark_path:
            return self._generate_bark(text, out_path, language, emotion, speaker)

        tts_binary = os.environ.get("TTS_BINARY", "")
        if tts_binary:
            return self._generate_piper(text, out_path, language)

        return self._generate_fallback(text, out_path)

    def _generate_bark(
        self,
        text: str,
        out_path: Path,
        language: str,
        emotion: str,
        speaker: str | None,
    ) -> Path:
        """Generation via Bark (HuggingFace)."""
        try:
            from bark import SAMPLE_RATE, generate_audio, preload_models

            preload_models()

            history_prompt = self._bark_history_prompt(language, emotion, speaker)
            audio_array = generate_audio(text, history_prompt=history_prompt)

            # Convertir en WAV
            out_path.parent.mkdir(parents=True, exist_ok=True)
            import numpy as np

            audio_int16 = (audio_array * 32767).astype(np.int16)
            with wave.open(str(out_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())

            logger.info("Bark TTS genere: %s (%d samples)", out_path, len(audio_array))
            return out_path

        except ImportError:
            logger.warning("Bark non installe, fallback deterministe")
            return self._generate_fallback(text, out_path)

    def _generate_piper(self, text: str, out_path: Path, language: str) -> Path:
        """Generation via Piper TTS (binaire local)."""
        import subprocess

        tts_binary = os.environ.get("TTS_BINARY", "")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        voice_map = {
            "fr": "fr_FR-siwis-medium",
            "en": "en_US-lessac-medium",
            "es": "es_ES-sharvard-medium",
            "de": "de_DE-karlsson-medium",
            "ja": "ja_JP-jsmedium",
        }
        voice = voice_map.get(language, voice_map["fr"])

        cmd = [tts_binary, "--model", voice, "--output_file", str(out_path)]
        try:
            result = subprocess.run(
                cmd, input=text, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.warning("Piper TTS erreur: %s", result.stderr[:200])
                return self._generate_fallback(text, out_path)
            return out_path
        except Exception:
            return self._generate_fallback(text, out_path)

    def _generate_fallback(self, text: str, out_path: Path) -> Path:
        """Fallback deterministe : tone pulse base sur la longueur du texte."""
        duration = max(0.5, min(10.0, len(text) * 0.05))
        freq = 200.0
        samples = []
        for t in range(int(duration * _RATE)):
            val = int(0.2 * 32767 * __import__("math").sin(2 * 3.14159 * freq * t / _RATE))
            samples.append(val)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_RATE)
            wf.writeframes(b"".join(struct.pack("<h", max(-32768, min(32767, s))) for s in samples))

        return out_path

    def _bark_history_prompt(
        self, language: str, emotion: str, speaker: str | None
    ) -> str | None:
        """Construit le history prompt pour Bark."""
        lang_map = {"fr": "v2/fr", "en": "v2/en", "de": "v2/de", "es": "v2/es"}
        bark_lang = lang_map.get(language, "v2/en")
        emotion_map = {
            "happy": "_happy",
            "sad": "_sad",
            "angry": "_angry",
            "fearful": "_fearful",
            "surprised": "_surprised",
        }
        suffix = emotion_map.get(emotion, "")
        speaker_id = speaker or "speaker_0"
        return f"{bark_lang}/{speaker_id}{suffix}"

    def mix_tracks(
        self,
        tracks: list[tuple[Path, float]],
        out_path: Path,
        sample_rate: int = 44100,
    ) -> Path:
        """Mixe plusieurs pistes audio avec volumes donnes.

        tracks: liste de (chemin_wav, volume_0_1)
        """
        import wave as _wave

        mixed: dict[int, float] = {}

        for track_path, volume in tracks:
            if not track_path.exists():
                continue
            try:
                with _wave.open(str(track_path), "rb") as wf:
                    frames = wf.readframes(wf.getnframes())
                    wf.getframerate()
                    for i in range(0, len(frames) - 1, 2):
                        sample_idx = i // 2
                        val = struct.unpack("<h", frames[i : i + 2])[0]
                        mixed[sample_idx] = mixed.get(sample_idx, 0.0) + val * volume
            except Exception:
                continue

        if not mixed:
            return self._generate_silence(1.0, out_path)

        max_idx = max(mixed.keys())
        samples = [int(max(-32768, min(32767, mixed.get(i, 0.0)))) for i in range(max_idx + 1)]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with _wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))

        return out_path

    def _generate_silence(self, duration: float, out_path: Path) -> Path:
        """Genere un fichier silence."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        n_frames = int(duration * _RATE)
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_RATE)
            wf.writeframes(b"\x00\x00" * n_frames)
        return out_path
