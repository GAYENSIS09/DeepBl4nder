"""AudioPlugin : synthèse et inspection audio déterministes (stdlib wave)."""

from __future__ import annotations

import math
import random
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from DeepBl4nder.plugins.base import Plugin, PluginError

_RATE = 44100


@dataclass
class AudioPlugin(Plugin):
    """Génère des pistes déterministes (ton, silence, ambiance) et les inspecte."""

    name: str = "audio"
    description: str = "Synthèse et inspection audio déterministes (stdlib wave)."

    def available(self) -> bool:
        return True

    def generate_tone(self, frequency: float, duration: float, out_path: Path, amplitude: float = 0.25) -> Path:
        frames = _pcm16([int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t / _RATE)) for t in range(int(duration * _RATE))])
        return _write_wav(out_path, frames, _RATE)

    def generate_silence(self, duration: float, out_path: Path) -> Path:
        return _write_wav(out_path, _pcm16([0] * int(duration * _RATE)), _RATE)

    def generate_ambience(self, duration: float, out_path: Path, seed: int = 0) -> Path:
        """Bruit de fond déterministe (bruit blanc doux, seed fixe)."""
        rng = random.Random(seed)
        samples = [int(0.08 * 32767 * rng.uniform(-1.0, 1.0)) for _ in range(int(duration * _RATE))]
        return _write_wav(out_path, _pcm16(samples), _RATE)

    def inspect(self, path: Path) -> dict[str, float]:
        if not path.is_file():
            raise PluginError(f"audio file not found: {path}")
        with wave.open(str(path), "rb") as handle:
            return {
                "channels": float(handle.getnchannels()),
                "sample_rate": float(handle.getframerate()),
                "sample_width": float(handle.getsampwidth()),
                "duration": float(handle.getnframes() / max(handle.getframerate(), 1)),
            }


def _pcm16(samples: list[int]) -> bytes:
    return b"".join(struct.pack("<h", max(-32768, min(32767, sample))) for sample in samples)


def _write_wav(path: Path, frames: bytes, rate: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return path
