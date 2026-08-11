"""FFmpegPlugin : transcodage, multiplexage et extraction audio via ffmpeg.

Frontière d'intégration vers ffmpeg : `FFMPEG_EXE` permet de surcharger le
binaire. Toutes les opérations passent par la frontière de processus
(`deepblender.bridge.worker`).
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from deepblender.bridge.worker import WorkerCommand, WorkerProcess
from deepblender.plugins.base import Plugin, PluginError


@dataclass
class FFmpegPlugin(Plugin):
    """Frontière d'intégration ffmpeg (transcode, mux, audio)."""

    name: str = "ffmpeg"
    description: str = "Transcodage, multiplexage et extraction audio via ffmpeg."
    ffmpeg_exe: str | None = None
    timeout: float = 600.0

    def __post_init__(self) -> None:
        self._exe = self.ffmpeg_exe or os.environ.get("FFMPEG_EXE", "ffmpeg")
        self._worker = WorkerProcess()

    def available(self) -> bool:
        return shutil.which(self._exe) is not None

    def _run(self, *args: str) -> str:
        if not self.available():
            raise PluginError("ffmpeg not available (set FFMPEG_EXE or install ffmpeg)")
        result = self._worker.run(WorkerCommand(argv=[self._exe, *args], timeout=self.timeout))
        if not result.ok:
            raise PluginError(result.stderr or "ffmpeg failed")
        return result.stdout

    def transcode(self, source: Path, destination: Path, codec: str = "libx264", crf: str = "23") -> Path:
        self._run("-y", "-i", str(source), "-c:v", codec, "-crf", crf, str(destination))
        return destination

    def mux(self, video: Path, audio: Path, destination: Path) -> Path:
        self._run("-y", "-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", str(destination))
        return destination

    def extract_audio(self, source: Path, destination: Path, codec: str = "pcm_s16le") -> Path:
        self._run("-y", "-i", str(source), "-vn", "-c:a", codec, str(destination))
        return destination
