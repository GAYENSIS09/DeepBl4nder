"""Gestion du rendu Blender du pipeline.

Extrait de ``runner.py`` pour isoler la logique de rendu (single-shot,
parallel-shots, fusion ffmpeg) dans une classe testable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from deepblender.artifacts.provenance import ProvenanceGraph
from deepblender.artifacts.registry import Artifact, ArtifactRegistry
from deepblender.codegen.validator import validate_for_worker
from deepblender.domain.scene import BlenderScript, RenderOutput, SceneSpec, ShotSpec
from deepblender.plugins.registry import PluginRegistry
from deepblender.production.events import EventLog
from deepblender.production.checkpoints import CheckpointManager
from deepblender.production.plugins import PluginShortcuts
from deepblender.production.runs import ProductionRun

logger = logging.getLogger("deepblender.pipeline")


class RenderManager(PluginShortcuts):
    """Exécute le rendu Blender et la fusion des plans.

    Responsable de l'exécution du script Blender via la bridge, du rendu
    parallèle des plans, et de la fusion ffmpeg des vidéos produites.
    """

    def __init__(
        self,
        *,
        blender_bridge: Any,
        blender: Any,
        workdir: Path,
        artifacts: ArtifactRegistry,
        provenance: ProvenanceGraph,
        production_run: ProductionRun,
        event_log: EventLog,
        plugins: PluginRegistry,
        emit: Callable[[str, dict[str, Any]], None],
        charge: Callable[[str, Artifact | None], None],
        max_render_retries: int = 2,
        gpu_semaphore: asyncio.Semaphore | None = None,
        write_json: Callable[[str, Any], Path],
        mark_checkpoint: Callable[[str], None],
        get_director_art: Callable[[], str | None],
    ) -> None:
        self.blender_bridge = blender_bridge
        self.blender = blender
        self.workdir = workdir
        self.artifacts = artifacts
        self.provenance = provenance
        self.production_run = production_run
        self.event_log = event_log
        self.plugins = plugins
        self._emit = emit
        self._charge = charge
        self.max_render_retries = max_render_retries
        self._gpu_semaphore = gpu_semaphore or asyncio.Semaphore(4)
        self._write_json = write_json
        self._mark_checkpoint = mark_checkpoint
        self._get_director_art = get_director_art

    # ── rendu single-shot ───────────────────────────────────────────

    async def run_render(self, scene: SceneSpec, script: BlenderScript) -> RenderOutput | None:
        """Exécute le script Blender et produit une vidéo."""
        self.production_run.start_step("render")
        self._emit("step_started", {"step": "render", "agent": "BlenderBridge"})
        t0 = time.time()

        # If no blender bridge available, skip rendering (not a failure)
        if self.blender_bridge is None or not self.blender_bridge.available():
            self.event_log.append("render_skipped", {"reason": "blender not available"})
            self.production_run.complete_step("render")
            return None

        # Snapshot workdir before execution to detect newly created files
        workdir = self.workdir / "render"
        workdir.mkdir(parents=True, exist_ok=True)
        existing_files = {p.stat().st_mtime for p in workdir.rglob("*") if p.is_file()}

        # Max render retries (self-repair loop)
        max_retries = self.max_render_retries
        render_attempt = 0

        while render_attempt <= max_retries:
            if render_attempt > 0:
                self.event_log.append("render_retry", {"attempt": render_attempt, "max": max_retries})
                self._emit("step_retry", {"step": "render", "attempt": render_attempt})

            try:
                # Execute the script in Blender
                self.blender_bridge.run_script(script, workdir)

                # Detect newly created media files (created after our snapshot)
                new_files: list[Path] = []
                for p in workdir.rglob("*"):
                    if p.is_file() and p.suffix.lower() in (".mp4", ".avi", ".mov", ".png", ".exr", ".jpg", ".jpeg", ".webm"):
                        try:
                            if p.stat().st_mtime >= min(existing_files, default=0) and p.stat().st_size > 0:
                                new_files.append(p)
                        except OSError:
                            pass

                if not new_files:
                    raise RuntimeError("No media file produced by Blender script")

                # Pick the most recently modified valid media file
                video_path = max(new_files, key=lambda p: p.stat().st_mtime)

                # Blender Plugin : sauvegarder la scène .blend
                if self.blender_plugin and self.blender_plugin.available():
                    try:
                        blend_path = workdir / f"{script.scene_name}.blend"
                        self.blender_plugin.save_scene(script.scene_name, blend_path)
                    except Exception:
                        pass

                # Use render settings from SceneSpec
                total_duration = sum(shot.duration for shot in scene.shots) if scene.shots else 30.0
                fps = scene.shots[0].fps if scene.shots else 24
                raw_resolution = getattr(scene.render, "resolution", (1920, 1080))
                resolution: tuple[int, int] = (int(raw_resolution[0]), int(raw_resolution[1]))
                format_ext = getattr(scene.render, "format", video_path.suffix.lstrip("."))

                render_output = RenderOutput(
                    video_path=str(video_path),
                    scene_name=script.scene_name,
                    duration=total_duration,
                    fps=fps,
                    resolution=resolution,
                    format=format_ext,
                    version=script.version,
                )
                # Checkpoint rendu : le fichier le plus coûteux du pipeline.
                self._write_json(
                    "render_output.json",
                    {
                        "script_sha256": CheckpointManager.script_fingerprint(script.code),
                        "render_output": render_output.to_mapping(),
                    },
                )
                self._mark_checkpoint("render")

                # Register artifact
                artifact = self.artifacts.register(
                    Artifact(
                        type="render_output",
                        name=script.scene_name,
                        path=video_path,
                    )
                )
                director_art = self._get_director_art()
                if director_art:
                    self.provenance.record(director_art, artifact.id)

                # Storage : stocker le rendu
                if self.storage_plugin and self.storage_plugin.available():
                    try:
                        self.storage_plugin.store(video_path, f"renders/{script.scene_name}/v{script.version}.{format_ext}")
                    except Exception:
                        pass

                # Knowledge Graph : tracker le rendu
                if self.knowledge_graph_plugin and self.knowledge_graph_plugin.available():
                    try:
                        self.knowledge_graph_plugin.add_node(
                            f"render_{artifact.id}",
                            "Render",
                            {"scene": script.scene_name, "duration": total_duration},
                        )
                        if director_art:
                            self.knowledge_graph_plugin.add_edge(
                                f"scene_{director_art}",
                                f"render_{artifact.id}",
                                "produced",
                            )
                    except Exception:
                        pass

                self._charge("render", artifact)
                elapsed = round(time.time() - t0, 2)
                self._emit("step_completed", {"step": "render", "agent": "BlenderBridge", "elapsed_s": elapsed, "output": str(video_path)})
                self.production_run.complete_step("render")
                return render_output

            except Exception as e:
                render_attempt += 1
                if render_attempt > max_retries:
                    self.event_log.append("render_failed", {"error": str(e), "attempts": render_attempt})
                    elapsed = round(time.time() - t0, 2)
                    self._emit("step_failed", {"step": "render", "agent": "BlenderBridge", "elapsed_s": elapsed, "error": str(e), "attempts": render_attempt})
                    self.production_run.fail_step("render")
                    return None
                else:
                    # Self-repair: ask BlenderAgent to refine the script
                    if self.blender is not None and hasattr(self.blender, "refine_script"):
                        try:
                            feedback = f"Render attempt {render_attempt} failed: {e}. Fix the script to produce a valid output file."
                            script = await self.blender.refine_script(scene, feedback, script.version + 1)
                            # Update script path for next iteration
                            script_path = workdir / f"{script.scene_name}_v{script.version}.py"
                            script_path.write_text(script.code, encoding="utf-8")
                            continue
                        except Exception as refine_err:
                            self.event_log.append("refine_failed", {"error": str(refine_err)})

        return None

    # ── rendu parallèle par plans ───────────────────────────────────

    async def run_render_parallel_shots(self, scene: SceneSpec, script: BlenderScript) -> RenderOutput | None:
        """Rend chaque plan en parallèle et fusionne les résultats."""
        if not scene.shots or len(scene.shots) <= 1:
            return await self.run_render(scene, script)

        self.production_run.start_step("render")
        self._emit("step_started", {"step": "render", "agent": "BlenderBridge", "mode": "parallel_shots", "shot_count": len(scene.shots)})
        t0 = time.time()

        if self.blender_bridge is None or not self.blender_bridge.available():
            self.event_log.append("render_skipped", {"reason": "blender not available"})
            self.production_run.fail_step("render")
            return None

        # Create per-shot scene specs
        shot_scenes: list[SceneSpec] = []
        for i, shot in enumerate(scene.shots):
            shot_scene = SceneSpec(
                brief=scene.brief,
                environment=scene.environment,
                characters=scene.characters,
                shots=[shot],
                render=scene.render,
            )
            shot_scenes.append(shot_scene)

        # Semaphore to limit parallel GPU jobs
        semaphore = self._gpu_semaphore

        async def render_shot(shot_idx: int, shot_scene: SceneSpec, shot: ShotSpec) -> RenderOutput | None:
            async with semaphore:
                shot_workdir = self.workdir / "render" / f"shot_{shot_idx}"
                shot_workdir.mkdir(parents=True, exist_ok=True)

                # Generate script for this shot
                shot_script = await self.blender.build_script(shot_scene)
                shot_script.scene_name = f"{script.scene_name}_shot_{shot_idx}"

                # Validate and run
                validation = validate_for_worker(shot_script.code)
                if not validation.ok:
                    self.event_log.append("shot_validation_failed", {"shot": shot_idx, "errors": validation.errors})
                    return None

                try:
                    self.blender_bridge.run_script(shot_script, shot_workdir)
                except Exception as e:
                    self.event_log.append("shot_render_failed", {"shot": shot_idx, "error": str(e)})
                    return None

                # Find output
                new_files = [
                    p for p in shot_workdir.rglob("*")
                    if p.is_file() and p.suffix.lower() in (".mp4", ".avi", ".mov", ".png", ".exr", ".jpg", ".jpeg", ".webm")
                    and p.stat().st_size > 0
                ]
                if not new_files:
                    return None
                video_path = max(new_files, key=lambda p: p.stat().st_mtime)

                raw_resolution = getattr(scene.render, "resolution", (1920, 1080))
                return RenderOutput(
                    video_path=str(video_path),
                    scene_name=f"{script.scene_name}_shot_{shot_idx}",
                    duration=shot.duration,
                    fps=shot.fps,
                    resolution=(int(raw_resolution[0]), int(raw_resolution[1])),
                    format=getattr(scene.render, "format", video_path.suffix.lstrip(".")),
                    version=script.version,
                )

        # Execute all shots in parallel with limited concurrency
        shot_tasks = [
            render_shot(i, shot_scenes[i], scene.shots[i])
            for i in range(len(scene.shots))
        ]
        shot_results = await asyncio.gather(*shot_tasks, return_exceptions=True)

        # Collect valid outputs
        valid_outputs: list[RenderOutput] = []
        for i, result in enumerate(shot_results):
            if isinstance(result, RenderOutput):
                valid_outputs.append(result)
                # Register artifact
                artifact = self.artifacts.register(
                    Artifact(type="render_output", name=f"shot_{i}", path=Path(result.video_path))
                )
                director_art = self._get_director_art()
                if director_art:
                    self.provenance.record(director_art, artifact.id)
            elif isinstance(result, Exception):
                self.event_log.append("shot_error", {"shot": i, "error": str(result)})

        if not valid_outputs:
            elapsed = round(time.time() - t0, 2)
            self._emit("step_failed", {"step": "render", "agent": "BlenderBridge", "elapsed_s": elapsed, "error": "All shots failed"})
            self.production_run.fail_step("render")
            return None

        # For now, return the first valid output
        # In production, you'd use ffmpeg concat to merge them
        first_output = valid_outputs[0]

        # Merge with ffmpeg if multiple shots
        if len(valid_outputs) > 1 and self.ffmpeg_plugin and self.ffmpeg_plugin.available():
            merged_path = await self.merge_shot_videos(valid_outputs, script.scene_name)
            if merged_path:
                first_output = RenderOutput(
                    video_path=str(merged_path),
                    scene_name=script.scene_name,
                    duration=sum(o.duration for o in valid_outputs),
                    fps=valid_outputs[0].fps,
                    resolution=valid_outputs[0].resolution,
                    format=valid_outputs[0].format,
                    version=script.version,
                )

        self._charge("render", None)
        # Checkpoint rendu (mode plans parallèles) : vidéo fusionnée réutilisable.
        self._write_json(
            "render_output.json",
            {
                "script_sha256": CheckpointManager.script_fingerprint(script.code),
                "render_output": first_output.to_mapping(),
            },
        )
        self._mark_checkpoint("render")
        elapsed = round(time.time() - t0, 2)
        self._emit("step_completed", {"step": "render", "agent": "BlenderBridge", "elapsed_s": elapsed, "mode": "parallel_shots", "shots": len(valid_outputs)})
        self.production_run.complete_step("render")
        return first_output

    # ── fusion ffmpeg ───────────────────────────────────────────────

    async def merge_shot_videos(self, outputs: list[RenderOutput], base_name: str) -> Path | None:
        """Fusionne plusieurs vidéos avec ffmpeg concat."""
        workdir = self.workdir / "render" / "merged"
        workdir.mkdir(parents=True, exist_ok=True)

        # Create concat file
        concat_file = workdir / "concat.txt"
        lines = []
        for out in outputs:
            lines.append(f"file '{out.video_path}'")
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        output_path = workdir / f"{base_name}_merged.mp4"
        try:
            self.ffmpeg_plugin._run(
                "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path)
            )
            return output_path
        except Exception as e:
            self.event_log.append("merge_failed", {"error": str(e)})
            return None
