"""LipSyncPlugin : synchronisation levres avancee.

Convertit de l'audio en blendshapes/morph targets pour la synchro levres.
"""

from __future__ import annotations

import logging
import math
import os
import wave
from dataclasses import dataclass
from pathlib import Path

from deepblender.plugins.base import Plugin

logger = logging.getLogger("deepblender.plugins.lipsync")


# Phonemes de base映射到 blendshape weights
PHONEME_BLENDSHAPES: dict[str, dict[str, float]] = {
    "sil": {},  # silence
    "PP": {"mouthClose": 0.0, "mouthFunnel": 0.8, "mouthPucker": 0.2},
    "FF": {"mouthClose": 0.0, "mouthFunnel": 0.3, "mouthPucker": 0.0, "jawOpen": 0.3},
    "TH": {"mouthClose": 0.0, "jawOpen": 0.4, "mouthFunnel": 0.2},
    "DD": {"mouthClose": 0.0, "jawOpen": 0.3, "mouthLeft": 0.1, "mouthRight": 0.1},
    "kk": {"mouthClose": 0.0, "jawOpen": 0.2, "mouthFunnel": 0.4},
    "CH": {"mouthClose": 0.0, "jawOpen": 0.15, "mouthPucker": 0.3, "mouthLeft": 0.2},
    "SS": {"mouthClose": 0.0, "jawOpen": 0.1, "mouthLeft": 0.1, "mouthRight": 0.1},
    "nn": {"mouthClose": 0.0, "jawOpen": 0.05},
    "RR": {"mouthClose": 0.0, "jawOpen": 0.15, "mouthFunnel": 0.3},
    "aa": {"mouthClose": 0.0, "jawOpen": 0.8, "mouthFunnel": 0.3},
    "E": {"mouthClose": 0.0, "jawOpen": 0.5, "mouthLeft": 0.3, "mouthRight": 0.3},
    "ih": {"mouthClose": 0.0, "jawOpen": 0.3, "mouthLeft": 0.2, "mouthRight": 0.2},
    "oh": {"mouthClose": 0.0, "jawOpen": 0.6, "mouthFunnel": 0.5, "mouthPucker": 0.3},
    "ou": {"mouthClose": 0.0, "jawOpen": 0.4, "mouthFunnel": 0.7, "mouthPucker": 0.5},
}


@dataclass
class PhonemeTiming:
    """Timing d'un phoneme dans l'audio."""

    phoneme: str
    start_time: float
    end_time: float
    confidence: float = 1.0


@dataclass
class LipSyncFrame:
    """Frame de synchro levres."""

    time: float
    jawOpen: float = 0.0
    mouthFunnel: float = 0.0
    mouthPucker: float = 0.0
    mouthLeft: float = 0.0
    mouthRight: float = 0.0
    mouthClose: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "time": self.time,
            "jawOpen": self.jawOpen,
            "mouthFunnel": self.mouthFunnel,
            "mouthPucker": self.mouthPucker,
            "mouthLeft": self.mouthLeft,
            "mouthRight": self.mouthRight,
            "mouthClose": self.mouthClose,
        }


@dataclass
class LipSyncPlugin(Plugin):
    """Synchronisation levres : Whisper (local), Rhubarb, fallback RMS."""

    name: str = "lipsync"
    description: str = "Synchronisation levres : Whisper, Rhubarb, fallback RMS."

    def available(self) -> bool:
        return True  # Fallback RMS toujours disponible

    def extract_phonemes(self, audio_path: Path) -> list[PhonemeTiming]:
        """Extrait les phonemes d'un fichier audio."""
        whisper_path = os.environ.get("WHISPER_MODEL_PATH", "")
        if whisper_path:
            return self._extract_whisper(audio_path)

        rhubarb = os.environ.get("RHUBARB_BINARY", "")
        if rhubarb:
            return self._extract_rhubarb(audio_path)

        return self._extract_rms(audio_path)

    def _extract_whisper(self, audio_path: Path) -> list[PhonemeTiming]:
        """Extraction via Whisper (phonemes via alignement)."""
        try:
            import whisper

            model = whisper.load_model("base")
            result = model.transcribe(str(audio_path), word_timestamps=True)

            phonemes = []
            for segment in result.get("segments", []):
                for word_info in segment.get("words", []):
                    text = word_info.get("word", "").strip()
                    if text:
                        # Approximation : un mot = phonemes simples
                        for i, char in enumerate(text.lower()):
                            start = word_info["start"] + i * 0.05
                            end = start + 0.06
                            phoneme = self._char_to_phoneme(char)
                            phonemes.append(PhonemeTiming(
                                phoneme=phoneme,
                                start_time=start,
                                end_time=min(end, word_info["end"]),
                            ))
            return phonemes

        except Exception as exc:
            logger.warning("Whisper echoue: %s, fallback RMS", exc)
            return self._extract_rms(audio_path)

    def _extract_rhubarb(self, audio_path: Path) -> list[PhonemeTiming]:
        """Extraction via Rhubarb Lip Sync."""
        import subprocess
        rhubarb = os.environ.get("RHUBARB_BINARY", "rhubarb")
        try:
            result = subprocess.run(
                [rhubarb, "-f", "json", str(audio_path)],
                capture_output=True, text=True, timeout=30,
            )
            import json
            data = json.loads(result.stdout)
            return [
                PhonemeTiming(
                    phoneme=m["value"],
                    start_time=m["start"],
                    end_time=m["end"],
                )
                for m in data.get("mouthCues", [])
            ]
        except Exception:
            return self._extract_rms(audio_path)

    def _extract_rms(self, audio_path: Path) -> list[PhonemeTiming]:
        """Fallback : detection de volume RMS pour approximer les phonemes."""
        try:
            with wave.open(str(audio_path), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                sr = wf.getframerate()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()

            chunk_size = int(sr * 0.05)  # 50ms chunks
            phonemes = []

            for i in range(0, len(frames) - chunk_size * n_channels * sampwidth,
                          chunk_size * n_channels * sampwidth):
                chunk = frames[i:i + chunk_size * n_channels * sampwidth]
                samples = []
                for j in range(0, len(chunk) - sampwidth, sampwidth):
                    val = int.from_bytes(chunk[j:j+sampwidth], byteorder="little", signed=True)
                    samples.append(val)

                if not samples:
                    continue

                rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
                time_pos = i / (sr * n_channels * sampwidth)

                if rms < 0.02:
                    phoneme = "sil"
                elif rms < 0.08:
                    phoneme = "nn"
                elif rms < 0.15:
                    phoneme = "aa"
                elif rms < 0.25:
                    phoneme = "E"
                else:
                    phoneme = "oh"

                phonemes.append(PhonemeTiming(
                    phoneme=phoneme,
                    start_time=time_pos,
                    end_time=time_pos + 0.05,
                    confidence=min(1.0, rms * 5),
                ))

            return phonemes

        except Exception:
            return []

    def _char_to_phoneme(self, char: str) -> str:
        """Convertit un caractere en phoneme approximatif."""
        mapping = {
            "a": "aa", "e": "E", "i": "ih", "o": "oh", "u": "ou",
            "b": "PP", "p": "PP", "m": "PP",
            "f": "FF", "v": "FF",
            "d": "DD", "t": "DD", "n": "nn", "l": "nn",
            "g": "kk", "k": "kk", "h": "kk",
            "j": "CH", "ch": "CH", "s": "SS", "z": "SS",
            "r": "RR",
        }
        return mapping.get(char, "sil")

    def generate_blendshapes(
        self,
        phonemes: list[PhonemeTiming],
        fps: float = 24.0,
    ) -> list[LipSyncFrame]:
        """Genere des blendshapes a partir des phonemes."""
        if not phonemes:
            return []

        duration = max(p.end_time for p in phonemes)
        frames = []
        time_step = 1.0 / fps
        current_time = 0.0

        while current_time <= duration:
            # Trouver le phoneme actif a ce moment
            active_phoneme = "sil"
            for p in phonemes:
                if p.start_time <= current_time <= p.end_time:
                    active_phoneme = p.phoneme
                    break

            # Appliquer les blendshapes avec lissage
            bs = PHONEME_BLENDSHAPES.get(active_phoneme, {})
            frame = LipSyncFrame(
                time=current_time,
                jawOpen=bs.get("jawOpen", 0.0),
                mouthFunnel=bs.get("mouthFunnel", 0.0),
                mouthPucker=bs.get("mouthPucker", 0.0),
                mouthLeft=bs.get("mouthLeft", 0.0),
                mouthRight=bs.get("mouthRight", 0.0),
                mouthClose=bs.get("mouthClose", 0.0),
            )
            frames.append(frame)
            current_time += time_step

        # Lissage entre frames
        return self._smooth_frames(frames)

    def _smooth_frames(self, frames: list[LipSyncFrame], window: int = 3) -> list[LipSyncFrame]:
        """Lisse les blendshapes entre frames adjacentes."""
        if len(frames) <= window:
            return frames

        smoothed = []
        for i in range(len(frames)):
            start = max(0, i - window // 2)
            end = min(len(frames), i + window // 2 + 1)
            subset = frames[start:end]

            smoothed.append(LipSyncFrame(
                time=frames[i].time,
                jawOpen=sum(f.jawOpen for f in subset) / len(subset),
                mouthFunnel=sum(f.mouthFunnel for f in subset) / len(subset),
                mouthPucker=sum(f.mouthPucker for f in subset) / len(subset),
                mouthLeft=sum(f.mouthLeft for f in subset) / len(subset),
                mouthRight=sum(f.mouthRight for f in subset) / len(subset),
                mouthClose=sum(f.mouthClose for f in subset) / len(subset),
            ))

        return smoothed

    def export_json(self, frames: list[LipSyncFrame], out_path: Path) -> Path:
        """Exporte les blendshapes en JSON pour Blender/UE5."""
        import json

        data = {
            "fps": 24.0,
            "frame_count": len(frames),
            "blendshapes": [f.to_dict() for f in frames],
        }

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return out_path
