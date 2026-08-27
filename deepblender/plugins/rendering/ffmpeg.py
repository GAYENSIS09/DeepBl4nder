"""FFmpegPlugin : transcodage, color grading, export et mixage audio via FFmpeg.

Frontière d'intégration vers ffmpeg : `FFMPEG_EXE` permet de surcharger le
binaire. Toutes les opérations passent par la frontière de processus
(`DeepBl4nder.bridge.worker`).
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from DeepBl4nder.bridge.worker import WorkerCommand, WorkerProcess
from DeepBl4nder.plugins.base import Plugin, PluginError


logger = logging.getLogger("DeepBl4nder.plugins.ffmpeg")


# ════════════════════════════════════════════════════════════════
#  Presets
# ════════════════════════════════════════════════════════════════

@dataclass
class ColorGradePreset:
    """Preset de color grading."""

    name: str
    lut: str = ""
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    gamma: float = 1.0
    temperature: float = 0.0
    film_grain: float = 0.0
    vignette: float = 0.0

    def to_filter_string(self) -> str:
        filters = []
        if self.brightness != 0.0 or self.contrast != 1.0 or self.saturation != 1.0 or self.gamma != 1.0:
            filters.append(
                f"eq=brightness={self.brightness}:contrast={self.contrast}"
                f":saturation={self.saturation}:gamma={self.gamma}"
            )
        if self.temperature != 0:
            filters.append(f"colortemperature=temperature={self.temperature}")
        if self.film_grain > 0:
            filters.append(f"noise=alls={self.film_grain * 50}:allf=t")
        if self.vignette > 0:
            filters.append(f"vignette=angle=PI/{4 / self.vignette}")
        if self.lut:
            filters.append(f"lut3d=file='{self.lut}'")
        if self.name in ("cinematic", "warm", "cold"):
            cb_map = {
                "cinematic": "rs=0.05:gs=0.02:bs=-0.03:rm=0.03:gm=0.01:bm=-0.02",
                "warm": "rs=0.1:gs=0.05:bs=-0.05",
                "cold": "rs=-0.05:gs=0.0:bs=0.1",
            }
            if self.name in cb_map:
                filters.append(f"colorbalance={cb_map[self.name]}")
        return ",".join(filters) if filters else "null"


@dataclass
class ExportPreset:
    """Preset d'export video."""

    name: str
    codec: str = "libx264"
    pixel_format: str = "yuv420p"
    crf: int = 18
    bitrate: str = ""
    extra_args: list[str] | None = None

    def to_ffmpeg_args(self) -> list[str]:
        args = ["-c:v", self.codec, "-pix_fmt", self.pixel_format]
        if self.bitrate:
            args.extend(["-b:v", self.bitrate])
        else:
            args.extend(["-crf", str(self.crf)])
        if self.extra_args:
            args.extend(self.extra_args)
        return args


EXPORT_PRESETS = {
    "h264_1080p": ExportPreset(name="H.264 1080p", codec="libx264", pixel_format="yuv420p", crf=18),
    "h264_4k": ExportPreset(name="H.264 4K", codec="libx264", pixel_format="yuv420p", crf=16, extra_args=["-s", "3840x2160"]),
    "prores_422": ExportPreset(name="ProRes 422", codec="prores_ks", pixel_format="yuv422p10le", extra_args=["-profile:v", "2", "-vendor", "apl0"]),
    "prores_4444": ExportPreset(name="ProRes 4444", codec="prores_ks", pixel_format="yuva444p10le", extra_args=["-profile:v", "4", "-vendor", "apl0"]),
    "dnxhd": ExportPreset(name="DNxHD", codec="dnxhd", pixel_format="yuv422p", extra_args=["-b:v", "185M"]),
    "webm_vp9": ExportPreset(name="WebM VP9", codec="libvpx-vp9", pixel_format="yuv420p", extra_args=["-b:v", "0", "-crf", "30"]),
    "gif": ExportPreset(name="GIF", codec="gif", pixel_format="rgb24", extra_args=["-vf", "fps=15,scale=480:-1:flags=lanczos"]),
}

COLOR_GRADE_PRESETS = {
    "cinematic": ColorGradePreset(name="Cinema", contrast=1.2, saturation=0.85, temperature=200),
    "warm": ColorGradePreset(name="Chaud", brightness=0.02, saturation=1.1, temperature=400),
    "cold": ColorGradePreset(name="Froid", saturation=0.9, temperature=-300),
    "vintage": ColorGradePreset(name="Vintage", contrast=1.1, saturation=0.7, film_grain=0.3, vignette=0.5),
    "noir": ColorGradePreset(name="Noir & Blanc", saturation=0.0, contrast=1.3),
    "vivid": ColorGradePreset(name="Vif", saturation=1.4, contrast=1.1, brightness=0.03),
    "flat": ColorGradePreset(name="Plat", contrast=0.8, saturation=0.9, gamma=1.1),
}


# ════════════════════════════════════════════════════════════════
#  Plugin
# ════════════════════════════════════════════════════════════════

@dataclass
class FFmpegPlugin(Plugin):
    """Frontière d'intégration ffmpeg (transcode, mux, audio, color grading, export)."""

    name: str = "ffmpeg"
    description: str = "Transcodage, color grading, export et mixage audio via ffmpeg."
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

    def _run_path(self, *args: str) -> Path:
        """Run and return the last path argument."""
        self._run(*args)
        return Path(args[-1])

    # ── Base ──────────────────────────────────────────────────

    def transcode(self, source: Path, destination: Path, codec: str = "libx264", crf: str = "23") -> Path:
        self._run("-y", "-i", str(source), "-c:v", codec, "-crf", crf, str(destination))
        return destination

    def mux(self, video: Path, audio: Path, destination: Path) -> Path:
        self._run("-y", "-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", str(destination))
        return destination

    def extract_audio(self, source: Path, destination: Path, codec: str = "pcm_s16le") -> Path:
        self._run("-y", "-i", str(source), "-vn", "-c:a", codec, str(destination))
        return destination

    # ── Color Grading ─────────────────────────────────────────

    def color_grade(
        self,
        input_path: Path,
        output_path: Path,
        preset: str = "cinematic",
        custom: ColorGradePreset | None = None,
    ) -> Path:
        grade = custom or COLOR_GRADE_PRESETS.get(preset, COLOR_GRADE_PRESETS["cinematic"])
        filter_str = grade.to_filter_string()

        if filter_str == "null":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_path, output_path)
            return output_path

        self._run("-y", "-i", str(input_path), "-vf", filter_str, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(output_path))
        logger.info("Color grading applique: %s -> %s (%s)", input_path.name, output_path.name, preset)
        return output_path

    # ── Export ────────────────────────────────────────────────

    def export_video(
        self,
        input_path: Path,
        output_path: Path,
        preset: str = "h264_1080p",
        custom_preset: ExportPreset | None = None,
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
    ) -> Path:
        exp = custom_preset or EXPORT_PRESETS.get(preset, EXPORT_PRESETS["h264_1080p"])
        args = exp.to_ffmpeg_args()
        self._run("-y", "-i", str(input_path), *args, "-c:a", audio_codec, "-b:a", audio_bitrate, str(output_path))
        logger.info("Export termine: %s -> %s (%s)", input_path.name, output_path.name, exp.name)
        return output_path

    # ── Audio ─────────────────────────────────────────────────

    def mix_audio_tracks(
        self,
        tracks: list[tuple[Path, float]],
        output_path: Path,
        duration: float | None = None,
        sample_rate: int = 44100,
        normalize_lufs: bool = True,
        target_lufs: float = -14.0,
    ) -> Path:
        if not tracks:
            raise ValueError("Aucune piste audio fournie")

        cmd_args = ["-y"]
        for track_path, _ in tracks:
            cmd_args.extend(["-i", str(track_path)])

        n = len(tracks)
        if n == 1:
            cmd_args.extend(["-map", "0:a"])
        else:
            volumes = "".join(f"[{i}:a]volume={vol}[v{i}];" for i, (_, vol) in enumerate(tracks))
            mixed = "".join(f"[v{i}]" for i in range(n))
            filter_complex = f"{volumes}{mixed}amix=inputs={n}:duration=first[out]"
            cmd_args.extend(["-filter_complex", filter_complex, "-map", "[out]"])

        if duration:
            cmd_args.extend(["-t", str(duration)])

        cmd_args.extend(["-ar", str(sample_rate), "-ac", "2"])

        if normalize_lufs:
            cmd_args.extend(["-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=summary"])

        cmd_args.append(str(output_path))
        self._run(*cmd_args)
        logger.info("Mixage audio termine: %s (%d pistes, stereo, LUFS=%.1f)", output_path.name, n, target_lufs)
        return output_path


# ════════════════════════════════════════════════════════════════
#  Module-level convenience (backward compat)
# ════════════════════════════════════════════════════════════════

_default_plugin: FFmpegPlugin | None = None


def _get_plugin() -> FFmpegPlugin:
    global _default_plugin
    if _default_plugin is None:
        _default_plugin = FFmpegPlugin()
    return _default_plugin


def apply_color_grading(input_path: Path, output_path: Path, preset: str = "cinematic", custom: ColorGradePreset | None = None) -> Path:
    return _get_plugin().color_grade(input_path, output_path, preset, custom)


def export_video(input_path: Path, output_path: Path, preset: str = "h264_1080p", custom_preset: ExportPreset | None = None, audio_codec: str = "aac", audio_bitrate: str = "192k") -> Path:
    return _get_plugin().export_video(input_path, output_path, preset, custom_preset, audio_codec, audio_bitrate)


def mix_audio_tracks(tracks: list[tuple[Path, float]], output_path: Path, duration: float | None = None, sample_rate: int = 44100, normalize_lufs: bool = True, target_lufs: float = -14.0) -> Path:
    return _get_plugin().mix_audio_tracks(tracks, output_path, duration, sample_rate, normalize_lufs, target_lufs)
