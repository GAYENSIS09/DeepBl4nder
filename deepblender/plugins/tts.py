"""TTsPlugin : synthèse vocale via un moteur externe configurable."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from deepblender.bridge.worker import WorkerCommand, WorkerProcess
from deepblender.plugins.base import Plugin, PluginError


@dataclass
class TTSPlugin(Plugin):
    """Frontière d'intégration TTS : moteur externe configurable (TTS_BINARY)."""

    name: str = "tts"
    description: str = "Synthèse vocale via un moteur externe (TTS_BINARY)."
    tts_exe: str | None = None

    def __post_init__(self) -> None:
        self._exe = self.tts_exe or os.environ.get("TTS_BINARY", "")
        self._worker = WorkerProcess()

    def available(self) -> bool:
        return bool(self._exe) and shutil.which(self._exe) is not None

    def generate(self, text: str, out_path: Path, lang: str = "fr", voice: str = "default") -> Path:
        if not self.available():
            raise PluginError("TTS engine not available (set TTS_BINARY)")
        result = self._worker.run(
            WorkerCommand(
                argv=[self._exe, "--text", text, "--out", str(out_path), "--lang", lang, "--voice", voice],
                timeout=300.0,
            )
        )
        if not result.ok:
            raise PluginError(result.stderr or "tts failed")
        return out_path
