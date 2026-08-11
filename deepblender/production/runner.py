"""Runner du pipeline : relie les agents NOOA aux briques de production.

Branche ce qui existait sans être connecté : `ProductionRun` (corrélation,
étapes, reprise), `EventLog` (journal append-only), `ArtifactRegistry` +
provenance, `BudgetTracker` et la boucle de révision QA -> `RevisionSpec` ->
étape ciblée (ADD 01 : traçabilité, observabilité, fiabilité, coûts).

Déroulé principal : brief -> DirectorAgent -> BlenderScript -> validation AST ->
QAAgent. Si la spec échoue (validation ou rapport), une `RevisionSpec` cible
l'étape fautive et elle est rejouée, jusqu'à `max_revisions`. À épuisement,
le run passe `blocked` (intervention humaine).

Post-production (optionnel) : AudioAgent -> AudioPlugin, LocalizationAgent ->
SubtitlePlugin/TTSPlugin, CompositingAgent -> FFmpegPlugin.

Le runner est asynchrone (méthodes agentiques = coroutines) et testable sans
LLM réel : on injecte des agents stub ayant les mêmes signatures.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from deepblender.artifacts.provenance import ProvenanceGraph
from deepblender.artifacts.registry import Artifact, ArtifactRegistry
from deepblender.codegen.validator import ValidationReport, validate_for_worker
from deepblender.domain.project import Brief
from deepblender.domain.qa import Issue, IssueKind, QAReport, RevisionSpec
from deepblender.domain.scene import BlenderScript, SceneSpec, RenderOutput
from deepblender.domain.media import AudioPlan, AudioMaster, CompositeSpec, LanguagePackage
from deepblender.plugins.registry import PluginRegistry
from deepblender.production.budget import BudgetTracker
from deepblender.production.events import EventLog, ProductionEvent
from deepblender.production.runs import ProductionRun, ProductionStep

CostHook = Callable[[str], float]

_STEPS = ("director", "blender", "qa", "render")
_POST_STEPS = ("audio", "localization", "compositing")


class _ForwardingEventLog(EventLog):
    """EventLog qui relaie chaque événement persisté à un hook (temps réel)."""

    def __init__(self, path: Path, forward: Callable[[str, dict[str, Any]], None]) -> None:
        super().__init__(path)
        self._forward = forward

    def append(self, kind: str, payload: dict[str, Any] | None = None) -> ProductionEvent:
        event = super().append(kind, payload)
        self._forward(kind, event.payload)
        return event


@dataclass
class RunOutcome:
    """Résultat complet d'un run : état, artifacts, coûts et specs finales."""

    run: ProductionRun
    artifacts: ArtifactRegistry
    provenance: ProvenanceGraph
    budget: BudgetTracker | None
    scene: SceneSpec | None = None
    script: BlenderScript | None = None
    report: QAReport | None = None
    revisions: int = 0
    render_output: RenderOutput | None = None
    audio_plan: AudioPlan | None = None
    audio_master: AudioMaster | None = None
    composite_spec: CompositeSpec | None = None
    language_packages: list[LanguagePackage] | None = None


class PipelineRunner:
    """Exécute brief -> DirectorAgent -> BlenderAgent -> QAAgent sous production.

    Post-production : AudioAgent -> AudioPlugin, LocalizationAgent ->
    SubtitlePlugin/TTSPlugin, CompositingAgent -> FFmpegPlugin.

    Tous les plugins sont utilisés via un PluginRegistry unique.
    """

    def __init__(
        self,
        *,
        project_id: str,
        director: Any,
        blender: Any,
        qa: Any,
        workdir: Path,
        plugins: PluginRegistry | None = None,
        artifacts: ArtifactRegistry | None = None,
        provenance: ProvenanceGraph | None = None,
        budget: BudgetTracker | None = None,
        cost_hook: CostHook | None = None,
        max_revisions: int = 1,
        event_hook: Callable[[str, dict[str, Any]], None] | None = None,
        # Agents post-production optionnels
        audio: Any = None,
        localization: Any = None,
        compositing: Any = None,
        target_languages: list[str] | None = None,
        # Blender bridge pour l'exécution
        blender_bridge: Any = None,
    ) -> None:
        self.director = director
        self.blender = blender
        self.qa = qa
        # Post-production agents
        self.audio = audio
        self.localization = localization
        self.compositing = compositing
        self.target_languages = target_languages or []

        # Blender bridge for rendering
        self.blender_bridge = blender_bridge

        self.plugins = plugins or PluginRegistry()
        self.workdir = workdir
        self.artifacts = artifacts or ArtifactRegistry()
        self.provenance = provenance or ProvenanceGraph()
        self.budget = budget
        self.cost_hook = cost_hook or (lambda _step: 0.0)
        self.max_revisions = max_revisions
        self.event_hook = event_hook
        log_path = workdir / "events.jsonl"
        self.event_log = (
            _ForwardingEventLog(log_path, self._emit) if event_hook else EventLog(log_path)
        )
        self.production_run = ProductionRun(project_id=project_id, log=self.event_log)
        self._director_art: str | None = None

    def _emit(self, kind: str, payload: dict[str, Any]) -> None:
        """Relaye un événement persisté du journal vers le hook temps réel."""
        if self.event_hook is not None:
            self.event_hook(kind, payload)

    # Raccourcis pratiques pour accéder aux plugins
    @property
    def audio_plugin(self):
        return self.plugins.get("audio")

    @property
    def ffmpeg_plugin(self):
        return self.plugins.get("ffmpeg")

    @property
    def subtitle_plugin(self):
        return self.plugins.get("subtitle")

    @property
    def tts_plugin(self):
        return self.plugins.get("tts")

    @property
    def blender_plugin(self):
        return self.plugins.get("blender")

    @property
    def storage_plugin(self):
        return self.plugins.get("storage")

    @property
    def git_plugin(self):
        return self.plugins.get("git")

    @property
    def knowledge_graph_plugin(self):
        return self.plugins.get("knowledge-graph")

    @property
    def asset_library_plugin(self):
        return self.plugins.get("asset-library")

    async def run(self, brief: Brief) -> RunOutcome:
        """Exécute le pipeline complet et renvoie l'état final."""
        run = self.production_run
        run.status = "running"
        self.event_log.append("run_started", {"project_id": run.project_id})
        for name in _STEPS:
            run.add_step(ProductionStep(name=name))
        for name in _POST_STEPS:
            run.add_step(ProductionStep(name=name))

        # Enforcement déterministe du budget : refus d'exécuter si déjà dépassé.
        if self.budget is not None and self.budget.over_budget():
            run.status = "blocked"
            self.event_log.append("run_blocked", {"step": "budget", "reason": "budget exhausted"})
            return RunOutcome(
                run=run,
                artifacts=self.artifacts,
                provenance=self.provenance,
                budget=self.budget,
            )

        self._inject_run_history()

        scene = await self._plan(brief)
        script, script_path = await self._build(scene)
        validation = validate_for_worker(script.code)
        report = await self._assess(scene, script_path, validation, script)

        revisions = 0
        while not report.passed and revisions < self.max_revisions:
            target = self._target_step(report, validation)
            self._record_revision(target, report, revisions + 1)
            revisions += 1
            # Révision « informée » : injecte les issues QA dans le contexte NOOA
            # de l'agent ciblé (``revision_feedback``) avant de régénérer, au lieu
            # de rejouer l'étape à l'aveugle.
            self._inject_revision_feedback(target, report, revisions)
            self._inject_run_history()
            if target == "director":
                scene = await self._plan(brief)
            script, script_path = await self._build(scene)
            validation = validate_for_worker(script.code)
            report = await self._assess(scene, script_path, validation, script)

        # Post-production (only if QA passed)
        self._inject_run_history()
        render_output = None
        audio_plan = None
        audio_master = None
        composite_spec = None
        language_packages = []

        if report.passed:
            # Parallel post-production: render, audio, and localization run concurrently
            # Compositing waits for all three to finish.

            async def _run_render_task():
                return await self._run_render(scene, script)

            async def _run_audio_task():
                if self.audio and self.audio_plugin:
                    return await self._run_audio(scene)
                return None, None

            async def _run_localization_task():
                if self.localization and (self.subtitle_plugin or self.tts_plugin) and self._target_languages_for(scene):
                    return await self._run_localization(scene)
                return []

            render_output, audio_result, language_packages = await asyncio.gather(
                _run_render_task(),
                _run_audio_task(),
                _run_localization_task(),
            )

            audio_plan, audio_master = audio_result if audio_result[0] is not None else (None, None)

            # Compositing (needs render + audio + localization outputs)
            if self.compositing and self.ffmpeg_plugin:
                composite_spec = await self._run_compositing(scene, render_output, audio_plan)

            run.status = "completed"
            self.event_log.append("run_completed", {})
        else:
            run.status = "blocked"
            self.event_log.append("run_blocked", {"step": self._target_step(report, validation)})

        return RunOutcome(
            run=run,
            artifacts=self.artifacts,
            provenance=self.provenance,
            budget=self.budget,
            scene=scene,
            script=script,
            report=report,
            revisions=revisions,
            render_output=render_output,
            audio_plan=audio_plan,
            audio_master=audio_master,
            composite_spec=composite_spec,
            language_packages=language_packages,
        )

    async def _plan(self, brief: Brief) -> SceneSpec:
        self.production_run.start_step("director")
        self._emit("llm_call", {"step": "director", "agent": "DirectorAgent", "status": "started", "model": getattr(self.director, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        scene = await self.director.plan_scene(brief)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "director", "agent": "DirectorAgent", "status": "completed", "elapsed_s": elapsed, "model": getattr(self.director, '_get_model_id', lambda: 'unknown')()})
        path = self._write_json("scene_spec.json", _to_mapping(scene))
        artifact = self.artifacts.register(
            Artifact(type="scene_spec", name="scene", path=path, status="spec")
        )
        self.provenance.record(brief.id, artifact.id)
        self._director_art = artifact.id

        # Knowledge Graph : tracker la scène
        if self.knowledge_graph_plugin and self.knowledge_graph_plugin.available():
            self.knowledge_graph_plugin.add_node(
                f"scene_{artifact.id}",
                "Scene",
                {"brief": scene.brief[:100], "characters": len(scene.characters)},
            )

        self._charge("director", artifact)
        self.production_run.complete_step("director")
        return scene

    async def _build(self, scene: SceneSpec) -> tuple[BlenderScript, Path]:
        self.production_run.start_step("blender")
        self._emit("llm_call", {"step": "blender", "agent": "BlenderAgent", "status": "started", "model": getattr(self.blender, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        script = await self.blender.build_script(scene)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "blender", "agent": "BlenderAgent", "status": "completed", "elapsed_s": elapsed, "model": getattr(self.blender, '_get_model_id', lambda: 'unknown')()})
        path = self.workdir / _safe_name(script.scene_name or "scene") / "script.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script.code, encoding="utf-8")
        artifact = self.artifacts.register(
            Artifact(type="blender_script", name=script.scene_name or "scene", path=path)
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)

        # Git : version control du script
        if self.git_plugin and self.git_plugin.available():
            try:
                self.git_plugin.commit(path, f"script v{script.version}: {script.scene_name}")
            except Exception:
                pass  # Git failure should not block pipeline

        # Storage : stocker le script
        if self.storage_plugin and self.storage_plugin.available():
            try:
                self.storage_plugin.store(path, f"scripts/{script.scene_name}/v{script.version}.py")
            except Exception:
                pass  # Storage failure should not block pipeline

        # Blender Plugin : inspection de la scène
        if self.blender_plugin and self.blender_plugin.available():
            try:
                scene_info = self.blender_plugin.inspect_scene()
                self.event_log.append("scene_inspected", {"objects": len(scene_info.get("objects", []))})
            except Exception:
                pass  # Inspection failure should not block pipeline

        self._charge("blender", artifact)
        self.production_run.complete_step("blender")
        return script, path

    async def _assess(
        self,
        scene: SceneSpec,
        script_path: Path,
        validation: ValidationReport,
        script: BlenderScript,
    ) -> QAReport:
        self.production_run.start_step("qa")
        self._emit("llm_call", {"step": "qa", "agent": "QAAgent", "status": "started", "model": getattr(self.qa, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        # L'agent QA est sandboxé : on lui passe le code source en ligne plutôt
        # qu'un chemin hôte qu'il ne pourrait pas lire ("File not found").
        if not script_path.is_file():
            report = QAReport(
                passed=False,
                score=0.0,
                issues=[Issue(kind=IssueKind.TECHNICAL, message="script file missing", step="blender")],
            )
        else:
            report = await self.qa.assess(scene, str(script_path), code=script.code)
        if not validation.ok:
            issues = [
                Issue(kind=IssueKind.TECHNICAL, message=error, step="blender")
                for error in validation.errors
            ]
            report = QAReport(passed=False, score=0.0, issues=issues)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "qa", "agent": "QAAgent", "status": "completed", "elapsed_s": elapsed, "model": getattr(self.qa, '_get_model_id', lambda: 'unknown')(), "score": report.score})
        self._charge("qa", None)
        self.production_run.complete_step("qa")
        return report

    def _target_step(self, report: QAReport, validation: ValidationReport) -> str:
        if not validation.ok:
            return "blender"
        for issue in report.issues:
            if issue.step in ("director", "blender"):
                return issue.step
        return "blender"

    async def _run_render(self, scene: SceneSpec, script: BlenderScript) -> RenderOutput | None:
        """Exécute le script Blender et produit une vidéo."""
        self.production_run.start_step("render")
        self._emit("step_started", {"step": "render", "agent": "BlenderBridge"})
        t0 = time.time()

        # If no blender bridge available, skip rendering
        if self.blender_bridge is None or not self.blender_bridge.available():
            self.event_log.append("render_skipped", {"reason": "blender not available"})
            self.production_run.complete_step("render")
            return None

        try:
            # Execute the script in Blender
            workdir = self.workdir / "render"
            workdir.mkdir(parents=True, exist_ok=True)

            self.blender_bridge.run_script(script, workdir)

            # Blender Plugin : sauvegarder la scène .blend
            if self.blender_plugin and self.blender_plugin.available():
                try:
                    blend_path = workdir / f"{script.scene_name}.blend"
                    self.blender_plugin.save_scene(script.scene_name, blend_path)
                except Exception:
                    pass

            # Determine output path (script should render to workdir)
            video_path = workdir / f"{script.scene_name}_v{script.version}.mp4"
            if not video_path.exists():
                # Try alternative extensions
                for ext in [".mp4", ".avi", ".mov", ".png"]:
                    alt_path = workdir / f"{script.scene_name}_v{script.version}{ext}"
                    if alt_path.exists():
                        video_path = alt_path
                        break

            # Calculate total duration from scene
            total_duration = sum(shot.duration for shot in scene.shots) if scene.shots else 30.0
            fps = scene.shots[0].fps if scene.shots else 24

            render_output = RenderOutput(
                video_path=str(video_path),
                scene_name=script.scene_name,
                duration=total_duration,
                fps=fps,
                resolution=(1920, 1080),  # Default, should come from scene
                format=video_path.suffix.lstrip(".") if video_path.exists() else "mp4",
                version=script.version,
            )

            # Register artifact
            artifact = self.artifacts.register(
                Artifact(
                    type="render_output",
                    name=script.scene_name,
                    path=video_path,
                )
            )
            if self._director_art:
                self.provenance.record(self._director_art, artifact.id)

            # Storage : stocker le rendu
            if self.storage_plugin and self.storage_plugin.available():
                try:
                    self.storage_plugin.store(video_path, f"renders/{script.scene_name}/v{script.version}.mp4")
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
                    if self._director_art:
                        self.knowledge_graph_plugin.add_edge(
                            f"scene_{self._director_art}",
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
            self.event_log.append("render_failed", {"error": str(e)})
            elapsed = round(time.time() - t0, 2)
            self._emit("step_failed", {"step": "render", "agent": "BlenderBridge", "elapsed_s": elapsed, "error": str(e)})
            self.production_run.complete_step("render")
            return None

    async def _run_audio(self, scene: SceneSpec) -> tuple[AudioPlan, AudioMaster]:
        """Exécute AudioAgent -> AudioPlugin."""
        self.production_run.start_step("audio")
        self._emit("llm_call", {"step": "audio", "agent": "AudioAgent", "status": "started", "model": getattr(self.audio, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        audio_plan = await self.audio.plan_audio(scene)
        elapsed_llm = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "audio", "agent": "AudioAgent", "status": "completed", "elapsed_s": elapsed_llm, "model": getattr(self.audio, '_get_model_id', lambda: 'unknown')()})

        # Generate audio tracks via plugin
        workdir = self.workdir / "audio"
        workdir.mkdir(parents=True, exist_ok=True)

        # Generate ambience
        ambience_path = workdir / "ambience.wav"
        self.audio_plugin.generate_ambience(
            duration=sum(s.duration for s in scene.shots) or 30.0,
            out_path=ambience_path,
        )

        # Generate music tone (placeholder)
        music_path = workdir / "music.wav"
        self.audio_plugin.generate_tone(frequency=220.0, duration=10.0, out_path=music_path)

        audio_master = AudioMaster(
            path=str(workdir / "master.wav"),
            duration=sum(s.duration for s in scene.shots) or 30.0,
            channels=1,
            sample_rate=44100,
            language="fr",
        )

        # Register artifacts
        plan_artifact = self.artifacts.register(
            Artifact(type="audio_plan", name="audio", path=self._write_json("audio_plan.json", audio_plan.to_mapping()))
        )
        master_artifact = self.artifacts.register(
            Artifact(type="audio_master", name="master", path=Path(audio_master.path))
        )
        if self._director_art:
            self.provenance.record(self._director_art, plan_artifact.id)
            self.provenance.record(self._director_art, master_artifact.id)

        self._charge("audio", plan_artifact)
        self._charge("audio", master_artifact)
        self.production_run.complete_step("audio")
        return audio_plan, audio_master

    async def _run_compositing(
        self,
        scene: SceneSpec,
        render_output: RenderOutput | None = None,
        audio_plan: AudioPlan | None = None,
    ) -> CompositeSpec:
        """Exécute CompositingAgent -> FFmpegPlugin pour fusionner tout."""
        self.production_run.start_step("compositing")
        self._emit("llm_call", {"step": "compositing", "agent": "CompositingAgent", "status": "started", "model": getattr(self.compositing, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        composite_spec = await self.compositing.plan_compositing(scene)
        elapsed_llm = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "compositing", "agent": "CompositingAgent", "status": "completed", "elapsed_s": elapsed_llm, "model": getattr(self.compositing, '_get_model_id', lambda: 'unknown')()})

        workdir = self.workdir / "compositing"
        workdir.mkdir(parents=True, exist_ok=True)

        # Register composite spec artifact
        spec_artifact = self.artifacts.register(
            Artifact(type="composite_spec", name="compositing", path=self._write_json("composite_spec.json", composite_spec.to_mapping()))
        )
        if self._director_art:
            self.provenance.record(self._director_art, spec_artifact.id)

        # Merge everything with FFmpeg if available
        if self.ffmpeg_plugin and self.ffmpeg_plugin.available():
            await self._merge_final_output(scene, render_output, audio_plan, workdir)

        self._charge("compositing", spec_artifact)
        self.production_run.complete_step("compositing")
        return composite_spec

    async def _merge_final_output(
        self,
        scene: SceneSpec,
        render_output: RenderOutput | None,
        audio_plan: AudioPlan | None,
        workdir: Path,
    ) -> None:
        """Fusionne vidéo + audio + sous-titres en un seul fichier final."""
        if render_output is None:
            return

        video_path = Path(render_output.video_path)
        if not video_path.exists():
            return

        # Collect audio files
        audio_dir = self.workdir / "audio"
        ambience_path = audio_dir / "ambience.wav"
        music_path = audio_dir / "music.wav"

        # Find subtitles
        sub_dir = self.workdir / "localization" / "fr"
        srt_path = sub_dir / "subtitles.srt"

        # Build FFmpeg command
        output_path = workdir / f"{scene.environment.description[:30].strip() or 'final'}_v{render_output.version}.mp4"

        inputs = ["-y", "-i", str(video_path)]
        has_audio = False

        # Add audio inputs
        if ambience_path.exists():
            inputs.extend(["-i", str(ambience_path)])
            has_audio = True
        if music_path.exists():
            inputs.extend(["-i", str(music_path)])
            has_audio = True

        # Build filter complex for audio mixing
        if has_audio:
            filter_parts = []
            audio_inputs = []
            input_idx = 1  # 0 is video

            if ambience_path.exists():
                filter_parts.append(f"[{input_idx}:a]volume=0.3[ambience];")
                audio_inputs.append("[ambience]")
                input_idx += 1
            if music_path.exists():
                filter_parts.append(f"[{input_idx}:a]volume=0.5[music];")
                audio_inputs.append("[music]")
                input_idx += 1

            if len(audio_inputs) > 1:
                mix = "".join(audio_inputs) + f"amix=inputs={len(audio_inputs)}:duration=first[aout]"
                filter_parts.append(mix)
                filter_complex = "".join(filter_parts)
                outputs = ["-map", "0:v", "-map", "[aout]"]
                outputs.extend(["-filter_complex", filter_complex])
            elif audio_inputs:
                outputs = ["-map", "0:v", "-map", audio_inputs[0]]
            else:
                outputs = []
        else:
            outputs = []

        # Add subtitles if available
        if srt_path.exists():
            # Subtitles will be burned in or added as a stream
            pass  # TODO: implement subtitle burn-in

        # Build final command
        cmd = inputs + outputs + [
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "medium",
        ]
        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        cmd.append(str(output_path))

        try:
            self.ffmpeg_plugin._run(*cmd)

            # Register final output artifact
            artifact = self.artifacts.register(
                Artifact(type="final_output", name="final", path=output_path)
            )
            if self._director_art:
                self.provenance.record(self._director_art, artifact.id)

            # Storage : stocker la sortie finale
            if self.storage_plugin and self.storage_plugin.available():
                try:
                    self.storage_plugin.store(output_path, f"final/{scene.environment.description[:30]}_v{render_output.version}.mp4")
                except Exception:
                    pass

            # Knowledge Graph : tracker la sortie finale
            if self.knowledge_graph_plugin and self.knowledge_graph_plugin.available():
                try:
                    self.knowledge_graph_plugin.add_node(
                        f"output_{artifact.id}",
                        "FinalOutput",
                        {"scene": scene.environment.description[:30], "version": render_output.version},
                    )
                except Exception:
                    pass

        except Exception as e:
            self.event_log.append("merge_failed", {"error": str(e)})

    def _target_languages_for(self, scene: SceneSpec) -> list[str]:
        """Langues cibles de localisation : explicites + langues des personnages.

        Si ``target_languages`` est renseigné, on l'utilise tel quel. Sinon on
        dérive les langues parlées par les personnages (principale en premier)
        complétées par les langues par défaut de l'agent.
        """
        targets: list[str] = list(self.target_languages)
        if targets:
            return targets
        for char in scene.characters:
            for lang in char.spoken_languages():
                if lang not in targets:
                    targets.append(lang)
        for lang in self.localization.default_languages():
            if lang not in targets:
                targets.append(lang)
        return targets

    async def _run_localization(self, scene: SceneSpec) -> list[LanguagePackage]:
        """Exécute LocalizationAgent -> SubtitlePlugin/TTSPlugin pour chaque langue."""
        self.production_run.start_step("localization")
        self._emit("llm_call", {"step": "localization", "agent": "LocalizationAgent", "status": "started", "model": getattr(self.localization, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        language_packages = []
        targets = self._target_languages_for(scene)

        for lang in targets:
            package = await self.localization.plan_localization(scene, lang, languages=targets)
            if package is None:
                continue

            workdir = self.workdir / "localization" / lang
            workdir.mkdir(parents=True, exist_ok=True)

            # Generate subtitles if plugin available
            if self.subtitle_plugin and package.subtitles_path:
                from deepblender.plugins.media.subtitle import SubtitleEntry
                subtitle_entries = []
                # Convert package.dialogues to SubtitleEntry
                for i, dialogue in enumerate(package.dialogues):
                    if isinstance(dialogue, dict):
                        start = dialogue.get("start", i * 3.0)
                        end = dialogue.get("end", (i + 1) * 3.0)
                        text = dialogue.get("text", "")
                        character = dialogue.get("character", "")
                        subtitle_entries.append(SubtitleEntry(
                            index=i + 1,
                            start=start,
                            end=end,
                            text=f"{character}: {text}" if character else text
                        ))
                if subtitle_entries:
                    self.subtitle_plugin.generate(subtitle_entries, Path(package.subtitles_path))  # type: ignore[union-attr]

            # Generate voice if TTS plugin available
            if self.tts_plugin and package.voice_path and self.tts_plugin.available():
                # Concatenate dialogues for TTS
                full_text = " ".join(
                    d.get("text", "") if isinstance(d, dict) else str(d)
                    for d in package.dialogues
                )
                if full_text.strip():
                    self.tts_plugin.generate(full_text, Path(package.voice_path), lang=lang)

            package_artifact = self.artifacts.register(
                Artifact(type="language_package", name=lang, path=self._write_json(f"language_package_{lang}.json", package.to_mapping()))
            )
            if self._director_art:
                self.provenance.record(self._director_art, package_artifact.id)

            language_packages.append(package)
            self._charge("localization", package_artifact)

        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "localization", "agent": "LocalizationAgent", "status": "completed", "elapsed_s": elapsed, "model": getattr(self.localization, '_get_model_id', lambda: 'unknown')(), "languages": targets})
        self.production_run.complete_step("localization")
        return language_packages

    def _format_feedback(self, report: QAReport, revision: int) -> str:
        """Formate un feedback lisible pour l'agent à partir du rapport QA."""
        lines = [f"### Révision {revision} — QA échoué (score {report.score:.2f})"]
        lines.append("Issues à corriger :")
        for issue in report.issues:
            location = f" ({issue.step})" if issue.step else ""
            lines.append(f"- [{issue.kind.value}]{location} {issue.message}")
        if report.recommendations:
            lines.append("Recommandations :")
            lines.extend(f"- {rec}" for rec in report.recommendations)
        return "\n".join(lines)

    def _agents_with_context(self) -> list[tuple[Any, Any]]:
        """Couples (agent, context) des agents NOOA du pipeline (duck-typed)."""
        agents = (
            self.director,
            self.blender,
            self.qa,
            self.audio,
            self.localization,
            self.compositing,
        )
        pairs: list[tuple[Any, Any]] = []
        for agent in agents:
            if agent is None:
                continue
            context = getattr(agent, "context", None)
            if context is not None:
                pairs.append((agent, context))
        return pairs

    def _set_context(self, context: Any, key: str, value: str) -> None:
        """Écrit une variable de contexte NOOA (``set_static`` si disponible)."""
        set_static = getattr(context, "set_static", None)
        if callable(set_static):
            set_static(key, value)
        elif hasattr(context, "set"):
            context.set(key, value)

    def _inject_run_history(self) -> None:
        """Injecte l'historique récent du run (``run_history``) aux agents.

        Les agents voient les événements persistés (étapes, révisions, coûts)
        sans que le runner dépende de NOOA (duck-typing, voir test_decoupling).
        """
        events = self.event_log.load()
        if not events:
            return
        recent = events[-8:]
        summary = "\n".join(f"- {e.kind} {e.payload}" for e in recent)
        for _agent, context in self._agents_with_context():
            self._set_context(context, "run_history", summary)

    def _inject_revision_feedback(self, target: str, report: QAReport, revision: int) -> None:
        """Injecte le feedback QA dans le contexte NOOA de l'agent ciblé.

        L'agent (BlenderAgent / DirectorAgent) lit ensuite ``revision_feedback``
        via ``self.context`` pour corriger le tir lors de la régénération.
        Les agents stub (tests) sans ``context`` sont ignorés silencieusement.
        """
        agent = {"director": self.director, "blender": self.blender}.get(target)
        if agent is None:
            return
        context = getattr(agent, "context", None)
        if context is None:
            return
        feedback = self._format_feedback(report, revision)
        self._set_context(context, "revision_feedback", feedback)

    def _record_revision(self, target: str, report: QAReport, revision: int) -> None:
        revision_spec = RevisionSpec(
            issues=list(report.issues),
            target_step=target,
            instructions=self._format_feedback(report, revision),
        )
        path = self._write_json(f"revision_{revision}_{target}.json", _to_mapping(revision_spec))
        artifact = self.artifacts.register(
            Artifact(type="revision_spec", name=target, path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self.event_log.append(
            "revision_requested",
            {"target_step": target, "revision": revision, "artifact_id": artifact.id},
        )

    def _charge(self, step: str, artifact: Artifact | None) -> None:
        cost = self.cost_hook(step)
        if artifact is not None:
            artifact.cost = cost
        if self.budget is not None:
            self.budget.add_llm(cost)
        self.event_log.append("cost_recorded", {"step": step, "cost": cost})

    def _write_json(self, filename: str, data: Any) -> Path:
        path = self.workdir / _safe_name(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, default=str, ensure_ascii=False), encoding="utf-8")
        return path


def _to_mapping(obj: Any) -> dict[str, Any]:
    """Sérialisation typée des dataclasses du domaine en dict JSON-safe."""
    if hasattr(obj, "to_mapping"):
        return obj.to_mapping()
    return asdict(obj)


def _safe_name(name: str) -> str:
    """Réduit un nom d'agent à un nom de fichier sûr."""
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return cleaned.strip("._") or "scene"
