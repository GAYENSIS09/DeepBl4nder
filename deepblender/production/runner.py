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

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from deepblender.artifacts.provenance import ProvenanceGraph
from deepblender.artifacts.registry import Artifact, ArtifactRegistry
from deepblender.codegen.validator import ValidationReport, validate_for_worker
from deepblender.domain.project import Brief
from deepblender.domain.qa import Issue, IssueKind, QAReport, RevisionSpec
from deepblender.domain.scene import BlenderScript, SceneSpec
from deepblender.domain.media import AudioPlan, AudioMaster, CompositeSpec, LanguagePackage
from deepblender.plugins.registry import PluginRegistry
from deepblender.production.budget import BudgetTracker
from deepblender.production.events import EventLog
from deepblender.production.runs import ProductionRun, ProductionStep

CostHook = Callable[[str], float]

_STEPS = ("director", "blender", "qa")
_POST_STEPS = ("audio", "localization", "compositing")


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
    audio_plan: AudioPlan | None = None
    audio_master: AudioMaster | None = None
    composite_spec: CompositeSpec | None = None
    language_packages: list[LanguagePackage] | None = None


class PipelineRunner:
    """Exécute brief -> DirectorAgent -> BlenderAgent -> QAAgent sous production.

    Post-production optionnelle : AudioAgent -> AudioPlugin, LocalizationAgent ->
    SubtitlePlugin/TTSPlugin, CompositingAgent -> FFmpegPlugin.

    Les plugins sont fournis via un PluginRegistry unique (source unique).
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
        # Agents post-production optionnels
        audio: Any = None,
        localization: Any = None,
        compositing: Any = None,
        target_languages: list[str] | None = None,
    ) -> None:
        self.director = director
        self.blender = blender
        self.qa = qa
        # Post-production agents
        self.audio = audio
        self.localization = localization
        self.compositing = compositing
        self.target_languages = target_languages or []

        self.plugins = plugins or PluginRegistry()
        self.workdir = workdir
        self.artifacts = artifacts or ArtifactRegistry()
        self.provenance = provenance or ProvenanceGraph()
        self.budget = budget
        self.cost_hook = cost_hook or (lambda _step: 0.0)
        self.max_revisions = max_revisions
        self.production_run = ProductionRun(project_id=project_id, log=EventLog(workdir / "events.jsonl"))
        self._director_art: str | None = None

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

    async def run(self, brief: Brief) -> RunOutcome:
        """Exécute le pipeline complet et renvoie l'état final."""
        run = self.production_run
        run.status = "running"
        run.log.append("run_started", {"project_id": run.project_id})
        for name in _STEPS:
            run.add_step(ProductionStep(name=name))
        for name in _POST_STEPS:
            run.add_step(ProductionStep(name=name))

        scene = await self._plan(brief)
        script, script_path = await self._build(scene)
        validation = validate_for_worker(script.code)
        report = await self._assess(scene, script_path, validation)

        revisions = 0
        while not report.passed and revisions < self.max_revisions:
            target = self._target_step(report, validation)
            self._record_revision(target, report, revisions + 1)
            revisions += 1
            if target == "director":
                scene = await self._plan(brief)
            script, script_path = await self._build(scene)
            validation = validate_for_worker(script.code)
            report = await self._assess(scene, script_path, validation)

        # Post-production (only if QA passed)
        audio_plan = None
        audio_master = None
        composite_spec = None
        language_packages = []

        if report.passed:
            # Audio
            if self.audio and self.audio_plugin:
                audio_plan, audio_master = await self._run_audio(scene)
            # Compositing
            if self.compositing and self.ffmpeg_plugin:
                composite_spec = await self._run_compositing(scene)
            # Localization
            if self.localization and (self.subtitle_plugin or self.tts_plugin) and self.target_languages:
                language_packages = await self._run_localization(scene)

            run.status = "completed"
            run.log.append("run_completed", {})
        else:
            run.status = "blocked"
            run.log.append("run_blocked", {"step": self._target_step(report, validation)})

        return RunOutcome(
            run=run,
            artifacts=self.artifacts,
            provenance=self.provenance,
            budget=self.budget,
            scene=scene,
            script=script,
            report=report,
            revisions=revisions,
            audio_plan=audio_plan,
            audio_master=audio_master,
            composite_spec=composite_spec,
            language_packages=language_packages,
        )

    async def _plan(self, brief: Brief) -> SceneSpec:
        self.production_run.start_step("director")
        scene = await self.director.plan_scene(brief)
        path = self._write_json("scene_spec.json", _to_mapping(scene))
        artifact = self.artifacts.register(
            Artifact(type="scene_spec", name="scene", path=path, status="spec")
        )
        self.provenance.record(brief.id, artifact.id)
        self._director_art = artifact.id
        self._charge("director", artifact)
        self.production_run.complete_step("director")
        return scene

    async def _build(self, scene: SceneSpec) -> tuple[BlenderScript, Path]:
        self.production_run.start_step("blender")
        script = await self.blender.build_script(scene)
        path = self.workdir / _safe_name(script.scene_name or "scene") / "script.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script.code, encoding="utf-8")
        artifact = self.artifacts.register(
            Artifact(type="blender_script", name=script.scene_name or "scene", path=path)
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("blender", artifact)
        self.production_run.complete_step("blender")
        return script, path

    async def _assess(
        self,
        scene: SceneSpec,
        script_path: Path,
        validation: ValidationReport,
    ) -> QAReport:
        self.production_run.start_step("qa")
        report = await self.qa.assess(scene, script_path)
        if not validation.ok:
            issues = [
                Issue(kind=IssueKind.TECHNICAL, message=error, step="blender")
                for error in validation.errors
            ]
            report = QAReport(passed=False, score=0.0, issues=issues)
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

    async def _run_audio(self, scene: SceneSpec) -> tuple[AudioPlan, AudioMaster]:
        """Exécute AudioAgent -> AudioPlugin."""
        self.production_run.start_step("audio")
        audio_plan = await self.audio.plan_audio(scene)

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

    async def _run_compositing(self, scene: SceneSpec) -> CompositeSpec:
        """Exécute CompositingAgent -> FFmpegPlugin."""
        self.production_run.start_step("compositing")
        composite_spec = await self.compositing.plan_compositing(scene)

        # Generate render passes using Blender (via BlenderBridge) then composite with FFmpeg
        workdir = self.workdir / "compositing"
        workdir.mkdir(parents=True, exist_ok=True)

        # Register composite spec artifact
        spec_artifact = self.artifacts.register(
            Artifact(type="composite_spec", name="compositing", path=self._write_json("composite_spec.json", composite_spec.to_mapping()))
        )
        if self._director_art:
            self.provenance.record(self._director_art, spec_artifact.id)

        # If FFmpeg plugin available and we have render output, do actual compositing
        if self.ffmpeg_plugin and self.ffmpeg_plugin.available():
            # This would be called after Blender renders the passes
            # For now, register the intent; actual compositing happens in worker
            pass

        self._charge("compositing", spec_artifact)
        self.production_run.complete_step("compositing")
        return composite_spec

    async def _run_localization(self, scene: SceneSpec) -> list[LanguagePackage]:
        """Exécute LocalizationAgent -> SubtitlePlugin/TTSPlugin pour chaque langue."""
        self.production_run.start_step("localization")
        language_packages = []

        for lang in self.target_languages:
            package = await self.localization.plan_localization(scene, lang)

            workdir = self.workdir / "localization" / lang
            workdir.mkdir(parents=True, exist_ok=True)

            # Generate subtitles if plugin available
            if self.subtitle_plugin and package.subtitles_path:
                from deepblender.plugins.subtitle import SubtitleEntry
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
                    self.subtitle_plugin.generate(subtitle_entries, Path(package.subtitles_path))

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

        self.production_run.complete_step("localization")
        return language_packages

    def _record_revision(self, target: str, report: QAReport, revision: int) -> None:
        revision_spec = RevisionSpec(
            issues=list(report.issues),
            target_step=target,
            instructions=f"Révision {revision} après échec QA, étape ciblée : {target}.",
        )
        path = self._write_json(f"revision_{revision}_{target}.json", _to_mapping(revision_spec))
        artifact = self.artifacts.register(
            Artifact(type="revision_spec", name=target, path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self.production_run.log.append(
            "revision_requested",
            {"target_step": target, "revision": revision, "artifact_id": artifact.id},
        )

    def _charge(self, step: str, artifact: Artifact | None) -> None:
        cost = self.cost_hook(step)
        if artifact is not None:
            artifact.cost = cost
        if self.budget is not None:
            self.budget.add_llm(cost)
        self.production_run.log.append("cost_recorded", {"step": step, "cost": cost})

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
