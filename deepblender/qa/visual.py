"""QA visuelle sur pixels rendus : détection frames noires, durée, résolution.

Pas de dépendance lourde : utilise ffmpeg/ffprobe (binaires déjà plugins).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepblender.domain.qa import Issue, IssueKind, QAReport
from deepblender.domain.scene import RenderOutput


@dataclass
class VisualQAResult:
    """Résultat de l'analyse visuelle d'un fichier média."""

    black_frame_ratio: float = 0.0
    duration_seconds: float | None = None
    resolution: tuple[int, int] | None = None
    format_name: str | None = None
    issues: list[Issue] = field(default_factory=list)


def _run_ffprobe(video_path: Path) -> dict[str, Any] | None:
    """Extrait métadonnées vidéo via ffprobe (JSON)."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def _run_blackdetect(video_path: Path) -> float:
    """Calcule le ratio de frames noires via ffmpeg blackdetect.

    Retourne un ratio 0.0-1.0 (1.0 = toutes les frames sont noires).
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(video_path),
                "-vf",
                "blackdetect=d=0.1:pix_th=0.10",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        stderr = result.stderr
        # Parse blackdetect output: "black_start:0.0 black_end:0.5 black_duration:0.5"
        black_durations = []
        for line in stderr.splitlines():
            match = re.search(r"black_duration:([\d.]+)", line)
            if match:
                black_durations.append(float(match.group(1)))
        total_black = sum(black_durations)
        # We need total duration to compute ratio; ffprobe is better for that
        return total_black
    except (subprocess.TimeoutExpired, OSError):
        return 0.0


def assess_render(render_output: RenderOutput) -> VisualQAResult:
    """Analyse un rendu pour détecter problèmes visuels évidents.

    Vérifications :
    - Fichier existe et non vide
    - Ratio de frames noires < 30% (seuil configurable)
    - Durée réelle vs spec (±10% tolérance)
    - Résolution réelle vs spec
    """
    result = VisualQAResult()
    video_path = Path(render_output.video_path)

    if not video_path.exists():
        result.issues.append(
            Issue(kind=IssueKind.VISUAL, message=f"Render file missing: {video_path}", step="render")
        )
        return result

    if video_path.stat().st_size == 0:
        result.issues.append(
            Issue(kind=IssueKind.VISUAL, message=f"Render file empty: {video_path}", step="render")
        )
        return result

    # ffprobe pour métadonnées
    probe = _run_ffprobe(video_path)
    if probe:
        # Durée
        fmt = probe.get("format", {})
        dur_str = fmt.get("duration")
        if dur_str:
            try:
                result.duration_seconds = float(dur_str)
            except ValueError:
                pass

        # Résolution (premier stream vidéo)
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video":
                w = stream.get("width")
                h = stream.get("height")
                if w and h:
                    result.resolution = (int(w), int(h))
                result.format_name = stream.get("codec_name")
                break

    # Blackdetect
    total_black = _run_blackdetect(video_path)
    if result.duration_seconds and result.duration_seconds > 0:
        result.black_frame_ratio = min(1.0, total_black / result.duration_seconds)

        # Seuil : > 30% noir = problème
        if result.black_frame_ratio > 0.30:
            result.issues.append(
                Issue(
                    kind=IssueKind.VISUAL,
                    message=f"High black frame ratio: {result.black_frame_ratio:.1%} (threshold 30%)",
                    step="render",
                )
            )

    # Cross-check durée vs spec
    spec_duration = render_output.duration
    if result.duration_seconds and spec_duration > 0:
        ratio = result.duration_seconds / spec_duration
        if ratio < 0.9 or ratio > 1.1:
            result.issues.append(
                Issue(
                    kind=IssueKind.VISUAL,
                    message=f"Duration mismatch: got {result.duration_seconds:.1f}s, expected {spec_duration:.1f}s (ratio {ratio:.2f})",
                    step="render",
                )
            )

    # Cross-check résolution vs spec
    spec_res = render_output.resolution
    if result.resolution and spec_res:
        if result.resolution != spec_res:
            result.issues.append(
                Issue(
                    kind=IssueKind.VISUAL,
                    message=f"Resolution mismatch: got {result.resolution[0]}x{result.resolution[1]}, expected {spec_res[0]}x{spec_res[1]}",
                    step="render",
                )
            )

    return result


def visual_qa_to_report(visual_result: VisualQAResult) -> QAReport:
    """Convertit VisualQAResult en QAReport pour le pipeline."""
    passed = len(visual_result.issues) == 0
    score = 1.0 if passed else max(0.0, 1.0 - visual_result.black_frame_ratio)
    return QAReport(
        passed=passed,
        score=score,
        issues=visual_result.issues,
        recommendations=[
            "Check Blender render settings (output path, file format)"
        ] if not passed else [],
    )