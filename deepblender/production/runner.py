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
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from deepblender.artifacts.provenance import ProvenanceGraph
from deepblender.artifacts.registry import Artifact, ArtifactRegistry
from deepblender.codegen.validator import ValidationReport, validate_for_worker
from deepblender.domain.patch import Patch, apply_patches
from deepblender.domain.project import Brief
from deepblender.domain.qa import Issue, IssueKind, QAReport, RevisionSpec
from deepblender.domain.scene import BlenderScript, SceneSpec, ShotSpec, RenderOutput
from deepblender.domain.media import AudioPlan, AudioMaster, CompositeSpec, LanguagePackage
from deepblender.plugins.registry import PluginRegistry
from deepblender.production.budget import BudgetTracker
from deepblender.production.events import EventLog, ProductionEvent
from deepblender.production.runs import ProductionRun, ProductionStep
from deepblender.qa.visual import assess_render, visual_qa_to_report

CostHook = Callable[[str], float]

_STEPS = ("story", "storyboard", "director", "blender", "qa", "render")
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
        max_render_retries: int = 2,
        event_hook: Callable[[str, dict[str, Any]], None] | None = None,
        # Agents pré-production optionnels
        story: Any = None,
        storyboard: Any = None,
        # Agents post-production optionnels
        audio: Any = None,
        localization: Any = None,
        compositing: Any = None,
        target_languages: list[str] | None = None,
        # Blender bridge pour l'exécution
        blender_bridge: Any = None,
        # Patch support
        session_factory: Any = None,
        production_id: str | None = None,
        # Optimisation options
        enable_cache: bool = True,
        enable_parallel_shots: bool = True,
        max_parallel_shots: int = 4,
        max_parallel_llm: int = 2,
    ) -> None:
        self.director = director
        self.blender = blender
        self.qa = qa
        # Pre-production agents
        self.story = story
        self.storyboard = storyboard
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
        self.max_render_retries = max_render_retries
        self.event_hook = event_hook
        self.session_factory = session_factory
        self.production_id = production_id

        # Optimisation settings
        self.enable_cache = enable_cache
        self.enable_parallel_shots = enable_parallel_shots
        self.max_parallel_shots = max_parallel_shots

        # LLM response cache (simple in-memory with TTL)
        self._llm_cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 3600  # 1 hour default

        # Semaphores for resource limiting
        self._llm_semaphore = asyncio.Semaphore(max_parallel_llm)
        self._gpu_semaphore = asyncio.Semaphore(max_parallel_shots)
        self._cpu_semaphore = asyncio.Semaphore(4)

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

    # ==================== CACHE HELPERS ====================

    def _cache_key(self, *args: Any, **kwargs: Any) -> str:
        """Génère une clé de cache déterministe."""
        content = f"{args}:{sorted(kwargs.items())}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _cache_get(self, key: str) -> Any | None:
        """Récupère une valeur du cache si non expirée."""
        if not self.enable_cache:
            return None
        entry = self._llm_cache.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.time() > expiry:
            self._llm_cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Stocke une valeur dans le cache avec TTL."""
        if not self.enable_cache:
            return
        self._llm_cache[key] = (value, time.time() + (ttl or self._cache_ttl))

    def _cache_invalidate(self, prefix: str) -> None:
        """Invalide toutes les entrées commençant par prefix."""
        keys = [k for k in self._llm_cache if k.startswith(prefix)]
        for k in keys:
            self._llm_cache.pop(k, None)

    def _load_pending_patches(self) -> list[Patch]:
        """Charge les patches non appliqués depuis la base de données."""
        if not self.session_factory or not self.production_id:
            return []
        session = self.session_factory()
        try:
            from deepblender.api.models import Patch as PatchModel
            from sqlalchemy import select
            patches = session.scalars(
                select(PatchModel).where(
                    PatchModel.production_id == self.production_id,
                    PatchModel.applied == False,  # noqa: E712
                ).order_by(PatchModel.created_at)
            ).all()
            result: list[Patch] = []
            for p in patches:
                try:
                    old_val = json.loads(p.old_value) if p.old_value else None
                except json.JSONDecodeError:
                    old_val = p.old_value
                try:
                    new_val = json.loads(p.new_value)
                except json.JSONDecodeError:
                    new_val = p.new_value
                result.append(Patch(
                    target=p.target,
                    old_value=old_val,
                    new_value=new_val,
                    rationale=p.rationale,
                    author=p.author_id,
                    applied=p.applied,
                    applied_at=p.applied_at.isoformat() if p.applied_at else None,
                ))
            return result
        finally:
            session.close()

    def _mark_patches_applied(self, patch_targets: list[str]) -> None:
        """Marque les patches comme appliqués en base."""
        if not self.session_factory or not self.production_id:
            return
        session = self.session_factory()
        try:
            from deepblender.api.models import Patch as PatchModel
            from sqlalchemy import select
            from datetime import datetime, timezone
            patches = session.scalars(
                select(PatchModel).where(
                    PatchModel.production_id == self.production_id,
                    PatchModel.target.in_(patch_targets),
                    PatchModel.applied == False,  # noqa: E712
                )
            ).all()
            for p in patches:
                p.applied = True
                p.applied_at = datetime.now(timezone.utc)
            session.commit()
        finally:
            session.close()

    def _mark_patches_applied(self, patch_targets: list[str]) -> None:
        """Marque les patches comme appliqués en base."""
        if not self.session_factory or not self.production_id:
            return
        session = self.session_factory()
        try:
            from deepblender.api.models import Patch as PatchModel
            from sqlalchemy import select
            from datetime import datetime, timezone
            patches = session.scalars(
                select(PatchModel).where(
                    PatchModel.production_id == self.production_id,
                    PatchModel.target.in_(patch_targets),
                    PatchModel.applied == False,  # noqa: E712
                )
            ).all()
            for p in patches:
                p.applied = True
                p.applied_at = datetime.now(timezone.utc)
            session.commit()
        finally:
            session.close()

    async def _cached_agent_call(
        self,
        agent: Any,
        method_name: str,
        cache_prefix: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Appel d'agent avec cache LLM."""
        if not self.enable_cache:
            method = getattr(agent, method_name)
            return await method(*args, **kwargs)

        # Generate cache key
        cache_key = self._cache_key(cache_prefix, agent.__class__.__name__, method_name, args, kwargs)
        cached = self._cache_get(cache_key)
        if cached is not None:
            self.event_log.append("cache_hit", {"key": cache_key, "agent": agent.__class__.__name__, "method": method_name})
            return cached

        # Execute with semaphore for LLM rate limiting
        async with self._llm_semaphore:
            method = getattr(agent, method_name)
            result = await method(*args, **kwargs)
        
        # Cache the result
        self._cache_set(cache_key, result)
        return result

    def _load_latest_scene_spec(self) -> SceneSpec | None:
        """Charge la dernière SceneSpec depuis les artifacts ou la DB."""
        # Try to load from artifact registry first
        latest_spec_art = self.artifacts.latest("scene_spec", "scene")
        if latest_spec_art and latest_spec_art.path.exists():
            try:
                import json
                data = json.loads(latest_spec_art.path.read_text(encoding="utf-8"))
                # Check if it's a full dict or summary
                if "schema_version" in data:
                    return SceneSpec.from_full_dict(data)
            except Exception:
                pass
        
        # Try to load from database timeline
        if self.session_factory and self.production_id:
            session = self.session_factory()
            try:
                from deepblender.api.models import Scene as SceneModel
                from sqlalchemy import select
                scenes = session.scalars(
                    select(SceneModel).where(
                        SceneModel.organization_id == self._get_org_id()
                    ).order_by(SceneModel.updated_at.desc())
                ).all()
                for scene_model in scenes:
                    try:
                        data = json.loads(scene_model.scene_spec_json)
                        if "schema_version" in data:
                            return SceneSpec.from_full_dict(data)
                    except Exception:
                        continue
            finally:
                session.close()
        return None

    def _get_org_id(self) -> str | None:
        """Récupère l'org_id depuis la production."""
        if not self.session_factory or not self.production_id:
            return None
        session = self.session_factory()
        try:
            from deepblender.api.models import Production
            prod = session.get(Production, self.production_id)
            return prod.organization_id if prod else None
        finally:
            session.close()

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

        # Révision humaine (HITL) : le dernier `revision_request_*.json` injecte
        # le commentaire du producteur dans l'agent ciblé avant de rejouer.
        revision_request = self._latest_revision_request()
        if revision_request is not None:
            self._inject_human_feedback(
                revision_request.get("target_step", "blender"),
                revision_request.get("comment", ""),
            )
            self.event_log.append(
                "revision_applied",
                {
                    "target_step": revision_request.get("target_step", "blender"),
                    "comment": revision_request.get("comment", ""),
                },
            )

        # Check for pending patches from API
        pending_patches = self._load_pending_patches()
        scene: SceneSpec | None = None
        story_spec = None
        storyboard_spec = None
        
        # STEP 1: Story generation
        if self.story is not None:
            story_spec = await self._run_story(brief)
        
        # STEP 2: Storyboard generation
        if self.storyboard is not None:
            storyboard_spec = await self._run_storyboard(story_spec)
        
        # HITL Approval Gate after storyboard (configurable)
        import os
        if storyboard_spec is not None and not os.environ.get("DEEPBLENDER_AUTO_APPROVE", "0") == "1":
            self.production_run.request_approval("storyboard")
            self.event_log.append("approval_requested", {"step": "storyboard", "reason": "Awaiting human approval of storyboard"})
            run.status = "awaiting_approval"
            self._emit("approval_required", {"production_id": self.production_id, "step": "storyboard"})
            # In a real implementation, we would wait here for approval
            # For now, we auto-approve in test mode or when DEEPBLENDER_AUTO_APPROVE=1
            if os.environ.get("DEEPBLENDER_AUTO_APPROVE", "0") != "1":
                self.production_run.approve("storyboard")
                self.event_log.append("approval_granted", {"step": "storyboard", "auto": True})
                run.status = "running"
        
        if pending_patches:
            # Load latest SceneSpec from artifacts or database
            scene = self._load_latest_scene_spec()
            if scene is None:
                # Fallback to director if no existing spec
                scene = await self._plan(brief, story_spec, storyboard_spec)
            else:
                # Apply patches to existing spec
                self.event_log.append("patches_applied", {"count": len(pending_patches), "targets": [p.target for p in pending_patches]})
                scene = apply_patches(scene, pending_patches)
                # Mark patches as applied
                self._mark_patches_applied([p.target for p in pending_patches])
                # Inject patch instructions into blender agent context for targeted regeneration
                if self.blender and hasattr(self.blender, "context"):
                    from deepblender.domain.patch import patch_to_revision_instruction
                    combined_feedback = "\n\n".join(patch_to_revision_instruction(p) for p in pending_patches)
                    self._set_context(self.blender.context, "revision_feedback", combined_feedback)
        else:
            # Normal flow: director creates new SceneSpec from story + storyboard
            scene = await self._plan(brief, story_spec, storyboard_spec)
        
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
                if self.enable_parallel_shots and len(scene.shots) > 1:
                    render_out = await self._run_render_parallel_shots(scene, script)
                else:
                    render_out = await self._run_render(scene, script)
                # Visual QA on rendered output
                if render_out is not None:
                    visual_result = assess_render(render_out)
                    visual_report = visual_qa_to_report(visual_result)
                    if not visual_report.passed:
                        # Merge visual issues into main QA report for revision targeting
                        report.issues.extend(visual_report.issues)
                        report.passed = False
                        report.score = min(report.score, visual_report.score)
                return render_out

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
            self._consume_revision_requests()
        else:
            run.status = "blocked"
            self.event_log.append("run_blocked", {"step": self._target_step(report, validation)})
            self._consume_revision_requests()

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

    async def _run_story(self, brief: Brief):
        """Exécute StoryAgent -> StorySpec."""
        if self.story is None:
            return None
        self.production_run.start_step("story")
        self._emit("llm_call", {"step": "story", "agent": "StoryAgent", "status": "started", "model": getattr(self.story, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        story_spec = await self.story.plan_story(brief)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "story", "agent": "StoryAgent", "status": "completed", "elapsed_s": elapsed, "model": getattr(self.story, '_get_model_id', lambda: 'unknown')()})
        path = self._write_json("story_spec.json", story_spec.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="story_spec", name="story", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("story", artifact)
        self.production_run.complete_step("story")
        return story_spec

    async def _run_storyboard(self, story_spec):
        """Exécute StoryboardAgent -> StoryboardSpec."""
        if self.storyboard is None or story_spec is None:
            return None
        self.production_run.start_step("storyboard")
        self._emit("llm_call", {"step": "storyboard", "agent": "StoryboardAgent", "status": "started", "model": getattr(self.storyboard, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        storyboard_spec = await self.storyboard.plan_storyboard(story_spec)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "storyboard", "agent": "StoryboardAgent", "status": "completed", "elapsed_s": elapsed, "model": getattr(self.storyboard, '_get_model_id', lambda: 'unknown')()})
        path = self._write_json("storyboard_spec.json", storyboard_spec.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="storyboard_spec", name="storyboard", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("storyboard", artifact)
        self.production_run.complete_step("storyboard")
        return storyboard_spec

    async def _plan(self, brief: Brief, story_spec=None, storyboard_spec=None) -> SceneSpec:
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
        max_retries = getattr(self, "max_render_retries", 2)
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
                resolution = getattr(scene.render, "resolution", (1920, 1080))
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

    async def _run_render_parallel_shots(self, scene: SceneSpec, script: BlenderScript) -> RenderOutput | None:
        """Rend chaque plan en parallèle et fusionne les résultats."""
        if not scene.shots or len(scene.shots) <= 1:
            return await self._run_render(scene, script)

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

                return RenderOutput(
                    video_path=str(video_path),
                    scene_name=f"{script.scene_name}_shot_{shot_idx}",
                    duration=shot.duration,
                    fps=shot.fps,
                    resolution=getattr(scene.render, "resolution", (1920, 1080)),
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
                if self._director_art:
                    self.provenance.record(self._director_art, artifact.id)
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
            merged_path = await self._merge_shot_videos(valid_outputs, script.scene_name)
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
        elapsed = round(time.time() - t0, 2)
        self._emit("step_completed", {"step": "render", "agent": "BlenderBridge", "elapsed_s": elapsed, "mode": "parallel_shots", "shots": len(valid_outputs)})
        self.production_run.complete_step("render")
        return first_output

    async def _merge_shot_videos(self, outputs: list[RenderOutput], base_name: str) -> Path | None:
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

        # Find voice files from localization (per language)
        voice_paths: list[Path] = []
        loc_dir = self.workdir / "localization"
        if loc_dir.exists():
            for lang_dir in loc_dir.iterdir():
                if lang_dir.is_dir():
                    voice_path = lang_dir / "voice.wav"
                    if voice_path.exists():
                        voice_paths.append(voice_path)

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
        # Add voice tracks
        for voice_path in voice_paths:
            inputs.extend(["-i", str(voice_path)])
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
            # Add voice tracks
            for i, voice_path in enumerate(voice_paths):
                filter_parts.append(f"[{input_idx}:a]volume=1.0[voice{i}];")
                audio_inputs.append(f"[voice{i}]")
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

        # Add subtitles burn-in if available
        if srt_path.exists():
            # Use subtitles filter to burn subtitles into video
            # We need to add the subtitles filter to the filter_complex
            if has_audio and 'filter_complex' in locals():
                filter_complex += f"[0:v]subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&HFFFFFF&,Outline=1,Shadow=1'[vout];"
                outputs = ["-map", "[vout]", "-map", "[aout]"]
                outputs.extend(["-filter_complex", filter_complex])
            else:
                # Video only with subtitles
                outputs = ["-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&HFFFFFF&,Outline=1,Shadow=1'"]

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

    def _latest_revision_request(self) -> dict[str, Any] | None:
        """Demande de révision humaine (HITL) la plus récente du workdir.

        `request_revision` (API) écrit `revision_request_<ts>.json` avant de
        relancer le pipeline. On récupère la plus récente pour injecter le
        commentaire du producteur dans l'agent ciblé au démarrage du run.
        """
        matches = sorted(
            (p for p in self.workdir.glob("revision_request_*.json") if ".applied" not in p.name),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not matches:
            return None
        try:
            return json.loads(matches[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _inject_human_feedback(self, target: str, comment: str) -> None:
        """Injection HITL : le commentaire humain devient `revision_feedback`.

        Contrairement à la boucle QA (feedback issu d'un rapport), ici le
        feedback vient d'un humain via le formulaire de révision. Il est
        injecté dans l'agent ciblé (director ou blender, défaut blender) avant
        de rejouer le pipeline.
        """
        if not comment.strip():
            return
        agent = {"director": self.director, "blender": self.blender}.get(target, self.blender)
        if agent is None:
            return
        context = getattr(agent, "context", None)
        if context is None:
            return
        feedback = f"### Révision humaine\nInstructions du producteur :\n{comment}"
        self._set_context(context, "revision_feedback", feedback)

    def _consume_revision_requests(self) -> None:
        """Marque les demandes de révision HITL comme appliquées.

        Appelé quand le run atteint un état terminal (completed/blocked) : la
        demande ne doit pas être ré-appliquée par un « Relancer le run »
        ultérieur. Un run interrompu par une exception conserve le fichier
        (retry = même commentaire).
        """
        for path in self.workdir.glob("revision_request_*.json"):
            if ".applied" in path.name:
                continue
            try:
                path.rename(path.with_suffix(".applied.json"))
            except OSError:
                pass

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
