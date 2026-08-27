"""Gestion des checkpoints de reprise du pipeline.

Extrait de ``runner.py`` pour isoler la logique de persistance des étapes
validées (brief fingerprint, chaîne de checkpoints, reprise depuis un run
interrompu).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Callable

from DeepBl4nder.domain.narrative import StorySpec, StoryboardSpec
from DeepBl4nder.domain.project import Brief
from DeepBl4nder.domain.qa import Issue, QAReport
from DeepBl4nder.domain.scene import BlenderScript, RenderOutput, SceneSpec
from DeepBl4nder.production.events import EventLog
from DeepBl4nder.production.runs import ProductionRun

logger = logging.getLogger("DeepBl4nder.pipeline")


def _safe_name(name: str) -> str:
    """Réduit un nom d'agent à un nom de fichier sûr."""
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return cleaned.strip("._") or "scene"


class CheckpointManager:
    """Gère les checkpoints de reprise du pipeline.

    Responsable de la persistance et de la lecture des étapes validées
    (story, storyboard, scene, script, report, render) dans le workdir,
    ainsi que du marquage des étapes comme « reprise possible ».
    """

    def __init__(
        self,
        *,
        workdir: Path,
        story: Any = None,
        storyboard: Any = None,
        animator: Any = None,
        write_json: Callable[[str, Any], Path],
        production_run: ProductionRun,
        emit: Callable[[str, dict[str, Any]], None],
        event_log: EventLog,
    ) -> None:
        self.workdir = workdir
        self.story = story
        self.storyboard = storyboard
        self.animator = animator
        self._write_json = write_json
        self.production_run = production_run
        self._emit = emit
        self.event_log = event_log
        self._current_brief_sha: str | None = None

    # ── fingerprints statiques ──────────────────────────────────────

    @staticmethod
    def brief_fingerprint(brief: Brief) -> str:
        """Empreinte du brief : change ⇒ tous les checkpoints sont invalidés."""
        return hashlib.sha256(brief.text.encode("utf-8")).hexdigest()

    @staticmethod
    def script_fingerprint(code: str) -> str:
        """Empreinte du code généré : lie rapports/rendus à leur script exact."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    # ── état de reprise ─────────────────────────────────────────────

    def _load_resume_state(self) -> dict[str, Any]:
        try:
            data = json.loads((self.workdir / "run_state.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _read_checkpoint_file(self, filename: str) -> Any | None:
        path = self.workdir / filename
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    # ── marquage ────────────────────────────────────────────────────

    def mark_checkpoint(self, step: str) -> None:
        """Marque une étape fraîchement complétée comme « reprise possible »."""
        if self._current_brief_sha is None:
            return
        state = self._load_resume_state()
        previous = {s for s in state.get("steps", []) if isinstance(s, str)}
        self._write_json(
            "run_state.json",
            {"brief_sha256": self._current_brief_sha, "steps": sorted(previous | {step})},
        )

    def reuse_step(self, name: str, payload: dict[str, Any] | None = None) -> None:
        """Étape servie depuis un checkpoint : marquée complétée sans ré-exécution."""
        self.production_run.mark_step(name, "completed")
        logger.info("[%s] étape %s reprise depuis un checkpoint", self.production_run.id, name)
        event = {"step": name, **(payload or {})}
        self._emit("step_resumed", event)
        self.event_log.append("step_resumed", event)

    # ── lecture des checkpoints individuels ──────────────────────────

    def checkpoint_story(self) -> StorySpec | None:
        data = self._read_checkpoint_file("story_spec.json")
        if not isinstance(data, dict):
            return None
        try:
            return StorySpec.from_mapping(data)
        except Exception:  # noqa: BLE001 - checkpoint corrompu : on repart à zéro
            return None

    def checkpoint_storyboard(self) -> StoryboardSpec | None:
        data = self._read_checkpoint_file("storyboard_spec.json")
        if not isinstance(data, dict):
            return None
        try:
            return StoryboardSpec.from_mapping(data)
        except Exception:  # noqa: BLE001
            return None

    def checkpoint_scene(self) -> SceneSpec | None:
        data = self._read_checkpoint_file("scene_spec.json")
        if not isinstance(data, dict) or "schema_version" not in data:
            return None
        try:
            return SceneSpec.from_full_dict(data)
        except Exception:  # noqa: BLE001
            return None

    def checkpoint_script(self) -> tuple[BlenderScript, Path] | None:
        meta = self._read_checkpoint_file("blender_script.json")
        if not isinstance(meta, dict):
            return None
        scene_name = str(meta.get("scene_name") or "")
        if not scene_name:
            return None
        path = self.workdir / _safe_name(scene_name) / "script.py"
        try:
            code = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        if not code.strip():
            return None
        version = int(meta.get("version", 1) or 1)
        return BlenderScript(code=code, scene_name=scene_name, version=version), path

    def checkpoint_report(self, script_code: str) -> QAReport | None:
        wrapper = self._read_checkpoint_file("qa_report.json")
        if not isinstance(wrapper, dict) or not wrapper.get("passed"):
            return None
        if wrapper.get("script_sha256") != self.script_fingerprint(script_code):
            return None
        try:
            issues = [
                Issue(kind=i["kind"], message=i["message"], step=i.get("step", ""))
                for i in wrapper.get("issues", [])
                if isinstance(i, dict)
            ]
            recommendations = [str(r) for r in wrapper.get("recommendations", [])]
            return QAReport(
                passed=True,
                score=float(wrapper.get("score", 0.0)),
                issues=issues,
                recommendations=recommendations,
            )
        except Exception:  # noqa: BLE001
            return None

    def checkpoint_render(self, script_code: str) -> RenderOutput | None:
        wrapper = self._read_checkpoint_file("render_output.json")
        if not isinstance(wrapper, dict):
            return None
        if wrapper.get("script_sha256") != self.script_fingerprint(script_code):
            return None
        data = wrapper.get("render_output")
        if not isinstance(data, dict) or not data.get("video_path"):
            return None
        video_path = Path(str(data["video_path"]))
        if not video_path.is_file():
            return None
        try:
            return RenderOutput(
                video_path=str(video_path),
                scene_name=str(data.get("scene_name", "")),
                duration=float(data.get("duration", 0.0)),
                fps=int(data.get("fps", 24)),
                resolution=(int(data["resolution"][0]), int(data["resolution"][1])),
                format=str(data.get("format", "mp4")),
                version=int(data.get("version", 1)),
            )
        except Exception:  # noqa: BLE001
            return None

    # ── chaîne de checkpoints ───────────────────────────────────────

    def load_checkpoints(self, brief: Brief) -> dict[str, Any]:
        """Chaîne de checkpoints valides : s'arrête au premier maillon manquant.

        Clés retournées (préfixe de la chaîne) : ``story``, ``storyboard``,
        ``scene``, ``script`` (tuple ``(BlenderScript, Path)``), ``report``
        et l'optionnel ``render`` (ne casse pas la chaîne).
        """
        state = self._load_resume_state()
        same_brief = state.get("brief_sha256") == self.brief_fingerprint(brief)
        done = (
            {s for s in state.get("steps", []) if isinstance(s, str)}
            if same_brief
            else set()
        )

        out: dict[str, Any] = {}
        # Les maillons amont ne comptent que si l'agent correspondant est actif :
        # un pipeline sans StoryAgent démarre sa chaîne au storyboard/directeur.
        if self.story is not None:
            if "story" not in done or (story := self.checkpoint_story()) is None:
                return out
            out["story"] = story
        if self.storyboard is not None:
            if (
                "storyboard" not in done
                or (storyboard := self.checkpoint_storyboard()) is None
            ):
                return out
            out["storyboard"] = storyboard
        if "director" not in done or (scene := self.checkpoint_scene()) is None:
            return out
        out["scene"] = scene
        if "blender" not in done or (script := self.checkpoint_script()) is None:
            return out
        out["script"] = script
        if "qa" in done and (rep := self.checkpoint_report(script[0].code)) is not None:
            out["report"] = rep
        # Le rendu est optionnel : son absence ne casse pas la chaîne.
        if "render" in done and (ro := self.checkpoint_render(script[0].code)) is not None:
            out["render"] = ro
        return out
