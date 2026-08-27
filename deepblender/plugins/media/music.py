"""MusicPlugin : generation musicale via ACE-Step / MusicGen.

Genere de la musique originale basee sur des descriptions textuelles.
"""

from __future__ import annotations

import logging
import math
import os
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from deepblender.plugins.base import Plugin

logger = logging.getLogger("deepblender.plugins.music")

_RATE = 44100


@dataclass
class MusicPlugin(Plugin):
    """Generation musicale : ACE-Step (local), MusicGen, fallback deterministe."""

    name: str = "music"
    description: str = "Generation musicale originale : ACE-Step, MusicGen, synthese."

    def available(self) -> bool:
        return True  # Fallback deterministe toujours disponible

    def generate_music(
        self,
        description: str,
        duration: float,
        out_path: Path,
        mood: str = "neutral",
        tempo: int = 120,
        key: str = "C",
        genre: str = "",
    ) -> Path:
        """Genere un fichier musical a partir d'une description."""
        ace_path = os.environ.get("ACE_STEP_MODEL_PATH", "")
        if ace_path:
            return self._generate_ace_step(description, duration, out_path, mood, tempo)

        musicgen_path = os.environ.get("MUSICGEN_MODEL_PATH", "")
        if musicgen_path:
            return self._generate_musicgen(description, duration, out_path, mood)

        return self._generate_deterministic(description, duration, out_path, mood, tempo, key)

    def _generate_ace_step(
        self,
        description: str,
        duration: float,
        out_path: Path,
        mood: str,
        tempo: int,
    ) -> Path:
        """Generation via ACE-Step (local model)."""
        try:
            from ace_step.pipeline import ACEStepPipeline

            pipe = ACEStepPipeline.from_pretrained("ACE-Step/ACE-Step-1.5B")
            pipe.to("cuda")

            result = pipe(
                prompt=description,
                duration=duration,
                guidance_scale=7.5,
                num_inference_steps=100,
            )

            audio = result.audios[0]
            import numpy as np

            audio_int16 = (audio.squeeze().cpu().numpy() * 32767).astype(np.int16)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(out_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(audio_int16.tobytes())

            logger.info("ACE-Step musique generee: %s", out_path)
            return out_path

        except Exception as exc:
            logger.warning("ACE-Step echoue: %s, fallback deterministe", exc)
            return self._generate_deterministic(description, duration, out_path, mood, tempo, "C")

    def _generate_musicgen(
        self,
        description: str,
        duration: float,
        out_path: Path,
        mood: str,
    ) -> Path:
        """Generation via MusicGen (Meta)."""
        try:
            from audiocraft.models import MusicGen

            model = MusicGen.get_pretrained("facebook/musicgen-small")
            model.set_generation_params(duration=int(duration))

            audio = model.generate([description])

            import numpy as np

            audio_np = audio.cpu().numpy().flatten()
            audio_int16 = (audio_np * 32767).astype(np.int16)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(out_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(32000)
                wf.writeframes(audio_int16.tobytes())

            logger.info("MusicGen musique generee: %s", out_path)
            return out_path

        except Exception as exc:
            logger.warning("MusicGen echoue: %s, fallback deterministe", exc)
            return self._generate_deterministic(description, duration, out_path, mood, 120, "C")

    def _generate_deterministic(
        self,
        description: str,
        duration: float,
        out_path: Path,
        mood: str,
        tempo: int,
        key: str,
    ) -> Path:
        """Synthese musicale deterministe (arpeges, accords, percussions)."""
        samples_per_beat = int(_RATE * 60.0 / tempo)
        total_samples = int(duration * _RATE)

        mood_config = {
            "happy": {"base_freq": 440.0, "scale": [0, 2, 4, 5, 7, 9, 11], "energy": 0.3},
            "sad": {"base_freq": 220.0, "scale": [0, 2, 3, 5, 7, 8, 10], "energy": 0.15},
            "epic": {"base_freq": 330.0, "scale": [0, 2, 4, 5, 7, 9, 11], "energy": 0.35},
            "dark": {"base_freq": 185.0, "scale": [0, 1, 3, 5, 6, 8, 10], "energy": 0.2},
            "neutral": {"base_freq": 261.6, "scale": [0, 2, 4, 5, 7, 9, 11], "energy": 0.2},
        }
        config = mood_config.get(mood, mood_config["neutral"])

        key_offsets = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        key_offset = key_offsets.get(key, 0)

        samples = []
        for i in range(total_samples):
            t = i / _RATE
            beat_pos = (i / samples_per_beat) % 8

            note_idx = int(beat_pos) % len(config["scale"])
            semitone = config["scale"][note_idx] + key_offset
            freq = config["base_freq"] * (2.0 ** (semitone / 12.0))

            val = config["energy"] * math.sin(2 * math.pi * freq * t)

            if int(beat_pos) % 4 == 0:
                val += 0.1 * math.sin(2 * math.pi * freq * 0.5 * t)

            envelope = 1.0 - (beat_pos % 1.0)
            val *= envelope

            sample_val = int(max(-32768, min(32767, val * 32767)))
            samples.append(sample_val)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_RATE)
            wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))

        logger.info("Musique deterministe generee: %s (%.1fs)", out_path, duration)
        return out_path
