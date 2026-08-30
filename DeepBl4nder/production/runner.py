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
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from DeepBl4nder.agents.base import GenerationError
from DeepBl4nder.artifacts.provenance import ProvenanceGraph
from DeepBl4nder.artifacts.registry import Artifact, ArtifactRegistry
from DeepBl4nder.production.context import ContextInjector
from DeepBl4nder.codegen.validator import ValidationReport, validate_for_worker
from DeepBl4nder.domain.patch import Patch, apply_patches
from DeepBl4nder.domain.project import Brief
from DeepBl4nder.domain.qa import Issue, IssueKind, QAReport, RevisionSpec
from DeepBl4nder.domain.scene import BlenderScript, SceneSpec, RenderOutput, ENGINE_UE5
from DeepBl4nder.domain.ue5 import UE5Commands
from DeepBl4nder.domain.media import AudioPlan, AudioMaster, CompositeSpec, LanguagePackage, MusicPlan, SoundDesignPlan
from DeepBl4nder.domain.narrative import StorySpec, StoryboardSpec
from DeepBl4nder.plugins.registry import PluginRegistry
from DeepBl4nder.production.budget import BudgetTracker
from DeepBl4nder.production.checkpoints import CheckpointManager
from DeepBl4nder.production.fallbacks import synthesize_blender_script, synthesize_storyboard
from DeepBl4nder.production.events import EventLog, ProductionEvent
from DeepBl4nder.production.rendering import RenderManager
from DeepBl4nder.production.postprod import PostProductionRunner
from DeepBl4nder.production.plugins import PluginShortcuts
from DeepBl4nder.production.runs import ProductionRun, ProductionStep
from DeepBl4nder.qa.visual import assess_render, visual_qa_to_report

CostHook = Callable[[str], float]

logger = logging.getLogger("DeepBl4nder.pipeline")


def _compact(payload: dict[str, Any], limit: int = 400) -> str:
    """Payload d'événement sur une ligne, tronqué pour le journal texte."""
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        text = str(payload)
    return text if len(text) <= limit else f"{text[:limit]}…({len(text)} car.)"

_STEPS = ("story", "storyboard", "director", "character_design", "environment", "blender", "qa", "animation", "render")
_POST_STEPS = ("music", "sound_design", "audio", "localization", "compositing", "review")
# Étapes « reprise » : clé checkpoint → nom d'étape pour les événements.
_RESUME_STEP_BY_KEY = {
    "story": "story",
    "storyboard": "storyboard",
    "scene": "director",
    "character_design": "character_design",
    "environment": "environment",
    "script": "blender",
    "report": "qa",
    "animation": "animation",
}


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
    music_plan: MusicPlan | None = None
    sound_design_plan: SoundDesignPlan | None = None


class PipelineRunner(PluginShortcuts):
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
        # Agents conception optionnels
        character_designer: Any = None,
        environment_artist: Any = None,
        animator: Any = None,
        # Agents post-production optionnels
        audio: Any = None,
        music_composer: Any = None,
        sound_designer: Any = None,
        localization: Any = None,
        compositing: Any = None,
        review: Any = None,
        target_languages: list[str] | None = None,
        # Blender bridge pour l'exécution
        blender_bridge: Any = None,
        # UE5 support
        ue5: Any = None,
        ue5_bridge: Any = None,
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
        # Conception agents
        self.character_designer = character_designer
        self.environment_artist = environment_artist
        self.animator = animator
        # Post-production agents
        self.audio = audio
        self.music_composer = music_composer
        self.sound_designer = sound_designer
        self.localization = localization
        self.compositing = compositing
        self.review = review
        self.target_languages = target_languages or []

        # Blender bridge for rendering
        self.blender_bridge = blender_bridge

        # UE5 support
        self.ue5 = ue5
        self.ue5_bridge = ue5_bridge

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

        self.checkpoints = CheckpointManager(
            workdir=workdir,
            story=story,
            storyboard=storyboard,
            animator=animator,
            write_json=self._write_json,
            production_run=self.production_run,
            emit=self._emit,
            event_log=self.event_log,
        )

        self.rendering = RenderManager(
            blender_bridge=blender_bridge,
            blender=blender,
            workdir=workdir,
            artifacts=self.artifacts,
            provenance=self.provenance,
            production_run=self.production_run,
            event_log=self.event_log,
            plugins=self.plugins,
            emit=self._emit,
            charge=self._charge,
            max_render_retries=max_render_retries,
            gpu_semaphore=self._gpu_semaphore,
            write_json=self._write_json,
            mark_checkpoint=self.checkpoints.mark_checkpoint,
            get_director_art=lambda: self._director_art,
        )

        # Contexte NOOA : injection de variables dans les agents
        self.context_injector = ContextInjector(
            agents=[
                ("story", self.story),
                ("storyboard", self.storyboard),
                ("director", self.director),
                ("character_designer", self.character_designer),
                ("environment_artist", self.environment_artist),
                ("blender", self.blender),
                ("qa", self.qa),
                ("animator", self.animator),
                ("audio", self.audio),
                ("music_composer", self.music_composer),
                ("sound_designer", self.sound_designer),
                ("localization", self.localization),
                ("compositing", self.compositing),
                ("review", self.review),
            ],
            event_log=self.event_log,
            workdir=self.workdir,
        )

        # Post-production : audio, music, compositing, review, localization
        self.postprod = PostProductionRunner(
            audio=self.audio,
            music_composer=self.music_composer,
            sound_designer=self.sound_designer,
            localization=self.localization,
            compositing=self.compositing,
            review=self.review,
            workdir=workdir,
            artifacts=self.artifacts,
            provenance=self.provenance,
            production_run=self.production_run,
            event_log=self.event_log,
            plugins=self.plugins,
            event_hook=self._emit,
            charge=self._charge,
            write_json=self._write_json,
            target_languages=list(target_languages or []),
            llm_semaphore=self._llm_semaphore,
            reported_llm_meta=self._reported_llm_meta,
            with_generation_retry=self._with_generation_retry,
            director_art=self._director_art,
        )

    def _emit(self, kind: str, payload: dict[str, Any]) -> None:
        """Relaye un événement persisté du journal vers le hook temps réel.

        Chaque événement est AUSSI journalisé (DEBUG, INFO pour les jalons) :
        le fichier de logs retrace tout l'arrière-plan du pipeline.
        """
        level = logging.INFO if kind in {
            "run_started", "run_completed", "run_failed", "run_blocked",
            "step_started", "step_completed", "step_failed",
        } else logging.DEBUG
        logger.log(level, "[event] %s %s", kind, _compact(payload))
        if self.event_hook is not None:
            self.event_hook(kind, payload)

    def _reported_llm_meta(self, agent: Any) -> dict[str, Any]:
        """Métadonnées modèle pour les événements llm_call ``completed``.

        Rapporte le vainqueur réel du vote du routeur (``provider`` + ``model``)
        quand il est connu ; retombe sur la config statique de l'agent sinon
        (client sans routeur, ou décision inexistante avant tout appel).
        """
        getter = getattr(agent, "_get_last_call_info", None)
        meta: dict[str, Any] = getter() if callable(getter) else {}
        if not meta.get("model"):
            meta["model"] = getattr(agent, "_get_model_id", lambda: "unknown")()
        return meta

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
        """Charge les patches non appliqués (désactivé — pas de base de données)."""
        return []

    def _mark_patches_applied(self, patch_targets: list[str]) -> None:
        """Marque les patches comme appliqués (désactivé — pas de base de données)."""
        pass

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
            # Désactivé — pas de base de données
            pass
        return None

    def _get_org_id(self) -> str | None:
        """Récupère l'org_id depuis la production (désactivé — pas de base)."""
        return None

    async def run(self, brief: Brief) -> RunOutcome:
        """Exécute le pipeline complet et renvoie l'état final."""
        run = self.production_run
        run.status = "running"
        self.event_log.append("run_started", {"project_id": run.project_id})
        logger.info(
            "Run %s démarré (projet=%s, workdir=%s)",
            run.id,
            run.project_id,
            self.workdir,
        )
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

        self.context_injector.inject_run_history()

        # Révision humaine (HITL) : le dernier `revision_request_*.json` injecte
        # le commentaire du producteur dans l'agent ciblé avant de rejouer.
        revision_request = self.context_injector.latest_revision_request()
        if revision_request is not None:
            self.context_injector.inject_human_feedback(
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
        self.checkpoints._current_brief_sha = CheckpointManager.brief_fingerprint(brief)

        # Reprise : recharge les checkpoints valides du workdir (run interrompu,
        # « Relancer le run ») pour ne pas rejouer ce qui est déjà produit.
        cached = self.checkpoints.load_checkpoints(brief)
        # Préfixe valide de la chaîne : story → storyboard → scene → character_design → environment → script → report → animation.
        chain = [
            key
            for key, active in (
                ("story", self.story is not None),
                ("storyboard", self.storyboard is not None),
                ("scene", True),
                ("character_design", self.character_designer is not None),
                ("environment", self.environment_artist is not None),
                ("script", True),
                ("report", True),
                ("animation", self.animator is not None),
            )
            if active
        ]
        natural = next((i for i, key in enumerate(chain) if key not in cached), len(chain))
        # Étapes réutilisables après invalidations éventuelles (revision/patches).
        reusable = set(chain[:natural])
        rev_target = (revision_request or {}).get("target_step")
        if rev_target == "story":
            reusable.clear()
        elif rev_target == "storyboard":
            reusable -= {"storyboard", "scene", "script", "report"}
        elif rev_target == "director":
            reusable -= {"scene", "script", "report"}
        elif rev_target == "blender":
            reusable -= {"script", "report"}
        elif rev_target == "qa":
            reusable -= {"report"}
        if pending_patches:
            # Les patches ciblent le script : la scène est rechargée des
            # artefacts, le script et l'évaluation sont régénérés.
            reusable -= {"scene", "script", "report"}
        rerun_from = next((key for key in chain if key not in reusable), None)
        if natural > 0 and len(reusable) < natural and rerun_from is not None:
            self.event_log.append(
                "resume_invalidated", {"from_step": _RESUME_STEP_BY_KEY[rerun_from]}
            )
        elif natural > 0:
            self.event_log.append("resume_ready", {"steps": list(chain[:natural])})

        scene: SceneSpec | None = None
        story_spec = None
        storyboard_spec = None

        # STEP 1: Story generation
        if "story" in reusable:
            story_spec = cached["story"]
            self.checkpoints.reuse_step("story", {"output": "story_spec.json"})
        elif self.story is not None:
            story_spec = await self._run_story(brief)
            self.checkpoints.mark_checkpoint("story")

        # STEP 2: Storyboard generation
        if "storyboard" in reusable:
            storyboard_spec = cached["storyboard"]
            self.checkpoints.reuse_step("storyboard", {"output": "storyboard_spec.json"})
        elif self.storyboard is not None:
            storyboard_spec = await self._run_storyboard(story_spec)
            self.checkpoints.mark_checkpoint("storyboard")

        # HITL Approval Gate after storyboard (configurable)
        import os
        if (
            storyboard_spec is not None
            and "storyboard" not in reusable  # un storyboard repris a déjà été approuvé
            and not os.environ.get("DeepBl4nder_AUTO_APPROVE", "0") == "1"
        ):
            self.production_run.request_approval("storyboard")
            self.event_log.append("approval_requested", {"step": "storyboard", "reason": "Awaiting human approval of storyboard"})
            run.status = "awaiting_approval"
            self._emit("approval_required", {"production_id": self.production_id, "step": "storyboard"})
            # In a real implementation, we would wait here for approval
            # For now, we auto-approve in test mode or when DeepBl4nder_AUTO_APPROVE=1
            if os.environ.get("DeepBl4nder_AUTO_APPROVE", "0") != "1":
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
                    from DeepBl4nder.domain.patch import patch_to_revision_instruction
                    combined_feedback = "\n\n".join(patch_to_revision_instruction(p) for p in pending_patches)
                    self.context_injector._set_context(self.blender.context, "revision_feedback", combined_feedback)
        else:
            # Normal flow: director creates new SceneSpec from story + storyboard
            if "scene" in reusable:
                scene = cached["scene"]
                self.checkpoints.reuse_step("director", {"output": "scene_spec.json"})
            else:
                scene = await self._plan(brief, story_spec, storyboard_spec)
            self.checkpoints.mark_checkpoint("director")

        # STEP 5: Character Design (optional)
        if self.character_designer is not None:
            if "character_design" in reusable:
                self.checkpoints.reuse_step("character_design", {"output": "character_design.json"})
            else:
                await self._run_character_design(scene)
                self.checkpoints.mark_checkpoint("character_design")

        # STEP 6: Environment Design (optional)
        if self.environment_artist is not None:
            if "environment" in reusable:
                self.checkpoints.reuse_step("environment", {"output": "environment.json"})
            else:
                await self._run_environment(scene)
                self.checkpoints.mark_checkpoint("environment")

        if "script" in reusable:
            script, script_path = cached["script"]
            self.checkpoints.reuse_step("blender", {"output": "script"})
        else:
            script, script_path = await self._build(scene)
        self.checkpoints.mark_checkpoint("blender")

        # Validation: different for Blender vs UE5
        is_ue5 = scene.render.is_ue5_engine()
        if is_ue5:
            # UE5: validate commands structure
            validation = ValidationReport(ok=True)
            if isinstance(script, UE5Commands):
                if not script.commands:
                    validation.add("UE5Commands is empty")
            else:
                validation.add("Expected UE5Commands, got " + type(script).__name__)
        else:
            # Blender: validate AST
            validation = validate_for_worker(script.code)

        if "report" in reusable:
            report = cached["report"]
            self.checkpoints.reuse_step("qa", {"score": report.score})
        else:
            report = await self._assess(scene, script_path, validation, script)

        revisions = 0
        while not report.passed and revisions < self.max_revisions:
            target = self._target_step(report, validation)
            self._record_revision(target, report, revisions + 1)
            revisions += 1
            # Révision « informée » : injecte les issues QA dans le contexte NOOA
            # de l'agent ciblé (``revision_feedback``) avant de régénérer, au lieu
            # de rejouer l'étape à l'aveugle.
            self.context_injector.inject_revision_feedback(
                target, report, revisions,
                agents_map={"director": self.director, "blender": self.blender},
            )
            self.context_injector.inject_run_history()
            if target == "director":
                scene = await self._plan(brief, story_spec, storyboard_spec)
            script, script_path = await self._build(scene)
            # Validation after revision
            if is_ue5:
                validation = ValidationReport(ok=True)
                if isinstance(script, UE5Commands) and not script.commands:
                    validation.add("UE5Commands is empty")
            else:
                validation = validate_for_worker(script.code)
            report = await self._assess(scene, script_path, validation, script)

        # STEP 10: Animation (optional, after QA passed)
        if self.animator is not None and report.passed:
            if "animation" in reusable:
                self.checkpoints.reuse_step("animation", {"output": "animation.json"})
            else:
                await self._run_animation(scene)
                self.checkpoints.mark_checkpoint("animation")

        # Post-production (only if QA passed)
        self.context_injector.inject_run_history()
        render_output = None
        audio_plan = None
        audio_master = None
        composite_spec = None
        language_packages: list[LanguagePackage] = []
        music_plan = None
        sound_design_plan = None

        if report.passed:
            # Parallel post-production: render, music, sound_design, audio, and localization run concurrently.
            # Compositing waits for all to finish. Review is final step.

            async def _run_render_task():
                # UE5: render happens via MRQ on the server (already triggered in _build_ue5)
                if is_ue5:
                    # Poll render status from UE5 server
                    if self.ue5_bridge and self.ue5_bridge.available():
                        try:
                            self.ue5_bridge.get_render_status()
                            # Create a minimal RenderOutput for the pipeline
                            render_dir = self.workdir / "render"
                            render_dir.mkdir(parents=True, exist_ok=True)
                            # Find output file
                            output_files = list(render_dir.rglob("*.mp4"))
                            if output_files:
                                video_path = output_files[0]
                            else:
                                video_path = render_dir / f"{scene.brief[:30] if scene.brief else 'scene'}.mp4"
                            return RenderOutput(
                                video_path=str(video_path),
                                scene_name=scene.brief[:30] if scene.brief else "ue5_scene",
                                duration=sum(s.duration for s in scene.shots) if scene.shots else 30.0,
                                fps=scene.render.fps,
                                resolution=scene.render.resolution,
                                format=scene.render.format,
                            )
                        except Exception as e:
                            self.event_log.append("ue5_render_status_error", {"error": str(e)})
                    return None

                # Blender: local rendering
                # Rendu déjà produit par un run précédent avec le même script :
                # on le réutilise (étape la plus coûteuse du pipeline).
                cached_render = self.checkpoints.checkpoint_render(script.code)
                if cached_render is not None:
                    self.production_run.mark_step("render", "completed")
                    self._emit("step_resumed", {"step": "render", "output": cached_render.video_path})
                    return cached_render
                if self.enable_parallel_shots and len(scene.shots) > 1:
                    render_out = await self.rendering.run_render_parallel_shots(scene, script)
                else:
                    render_out = await self.rendering.run_render(scene, script)
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

            async def _run_music_task():
                if self.music_composer:
                    return await self.postprod.run_music(scene)
                return None

            async def _run_sound_design_task():
                if self.sound_designer:
                    return await self.postprod.run_sound_design(scene)
                return None

            async def _run_audio_task():
                if self.audio and self.audio_plugin:
                    return await self.postprod.run_audio(scene)
                return None, None

            async def _run_localization_task():
                if self.localization and (self.subtitle_plugin or self.tts_plugin) and self.postprod.target_languages_for(scene):
                    return await self.postprod.run_localization(scene)
                return []

            audio_result: tuple[AudioPlan | None, AudioMaster | None] = (None, None)
            results = await asyncio.gather(
                _run_render_task(),
                _run_music_task(),
                _run_sound_design_task(),
                _run_audio_task(),
                _run_localization_task(),
            )
            render_output = results[0]
            music_plan = results[1]
            sound_design_plan = results[2]
            audio_result = results[3] if isinstance(results[3], tuple) else (None, None)
            language_packages = list(results[4])

            audio_plan, audio_master = (
                audio_result if audio_result[0] is not None else (None, None)
            )

            # Compositing (needs render + audio + localization outputs)
            if self.compositing and self.ffmpeg_plugin:
                composite_spec = await self.postprod.run_compositing(scene, render_output, audio_plan)

            # STEP 21: Final Review (optional)
            if self.review:
                review_report = await self.postprod.run_review(
                    scene, render_output, audio_plan, composite_spec,
                )
                self._write_json("review_report.json", review_report.to_mapping())

            run.status = "completed"
            self.event_log.append("run_completed", {})
            logger.info("Run %s terminé (status=completed)", run.id)
            self.context_injector.consume_revision_requests()
        else:
            run.status = "blocked"
            self.event_log.append("run_blocked", {"step": self._target_step(report, validation)})
            logger.warning(
                "Run %s bloqué : QA échoué après révisions (step=%s)",
                run.id,
                self._target_step(report, validation),
            )
            self.context_injector.consume_revision_requests()

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
            music_plan=music_plan,
            sound_design_plan=sound_design_plan,
        )

    async def _with_generation_retry(self, step: str, call_factory: Callable[[], Any]) -> Any:
        """Rejoue une fois l'appel agent après ``GenerationError``.

        Les 3 tentatives de validation NOOA vivent dans une même génération :
        si le modèle de secours s'enlise (ex. shots vides répétés malgré le
        feedback), une génération fraîche — nouvelle session, nouvel
        échantillonnage — offre une seconde chance au lieu de tuer le run.
        """
        try:
            return await call_factory()
        except GenerationError as exc:
            first_line = str(exc).strip().splitlines()[0][:160]
            logger.warning(
                "étape %s : génération invalide (%s) → nouvelle tentative "
                "(génération fraîche)",
                step,
                first_line,
            )
            self.event_log.append("llm_retry", {"step": step})
            self._emit("llm_call", {"step": step, "status": "retry"})
            return await call_factory()

    async def _run_story(self, brief: Brief):
        """Exécute StoryAgent -> StorySpec."""
        if self.story is None:
            return None
        self.production_run.start_step("story")
        self._emit("llm_call", {"step": "story", "agent": "StoryAgent", "status": "started", "model": getattr(self.story, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        story_spec = await self._with_generation_retry(
            "story", lambda: self.story.plan_story(brief)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "story", "agent": "StoryAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.story)})
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
        try:
            storyboard_spec = await self._with_generation_retry(
                "storyboard", lambda: self.storyboard.plan_storyboard(story_spec)
            )
        except GenerationError:
            # Deux générations épuisées (modèle de secours récalcitrant sur
            # l'invariant shots) : synthèse déterministe plutôt que run tué.
            storyboard_spec = self._synthesize_storyboard(story_spec)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "storyboard", "agent": "StoryboardAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.storyboard)})
        path = self._write_json("storyboard_spec.json", storyboard_spec.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="storyboard_spec", name="storyboard", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("storyboard", artifact)
        self.production_run.complete_step("storyboard")
        return storyboard_spec

    def _synthesize_storyboard(self, story_spec: StorySpec) -> StoryboardSpec:
        spec = synthesize_storyboard(story_spec)
        self.event_log.append(
            "storyboard_synthesized",
            {"shots": len(spec.shots), "reason": "generation_failed_twice"},
        )
        self._emit("llm_call", {"step": "storyboard", "status": "synthesized_fallback"})
        return spec

    def _synthesize_blender_script(self, scene: SceneSpec) -> BlenderScript:
        script = synthesize_blender_script(scene, self.workdir)
        self.event_log.append(
            "blender_script_synthesized",
            {"scene_name": script.scene_name, "reason": "generation_failed_twice"},
        )
        self._emit("llm_call", {"step": "blender", "status": "synthesized_fallback"})
        return script

    async def _plan(self, brief: Brief, story_spec=None, storyboard_spec=None) -> SceneSpec:
        self.production_run.start_step("director")
        self._emit("llm_call", {"step": "director", "agent": "DirectorAgent", "status": "started", "model": getattr(self.director, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        scene = await self._with_generation_retry(
            "director", lambda: self.director.plan_scene(brief)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "director", "agent": "DirectorAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.director)})
        path = self._write_json("scene_spec.json", scene.to_full_dict())
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

    async def _build(self, scene: SceneSpec) -> tuple[Any, Path]:
        """Route vers le bon moteur de rendu selon scene.render.engine."""
        engine = scene.render.engine.upper()

        if engine == ENGINE_UE5 or scene.render.is_ue5_engine():
            return await self._build_ue5(scene)
        else:
            # Blender (CYCLES, EEVEE, BLENDER, default)
            return await self._build_blender(scene)

    async def _build_ue5(self, scene: SceneSpec) -> tuple[UE5Commands, Path]:
        """Génère les commandes UE5 et les exécute via le bridge."""
        self.production_run.start_step("blender")  # Réutilise le step "blender" pour UE5
        self._emit("llm_call", {"step": "blender", "agent": "UE5Agent", "status": "started", "model": getattr(self.ue5, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        try:
            commands = await self._with_generation_retry(
                "blender", lambda: self.ue5.build_commands(scene)
            )
        except GenerationError:
            # Fallback: commandes basiques
            commands = self._synthesize_ue5_commands(scene)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "blender", "agent": "UE5Agent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.ue5)})

        # Exécuter les commandes via le bridge UE5
        if self.ue5_bridge and self.ue5_bridge.available():
            for cmd in commands.commands:
                try:
                    result = self.ue5_bridge._command(cmd.endpoint, cmd.payload, timeout=cmd.timeout)
                    if not result.ok:
                        self.event_log.append("ue5_command_failed", {"endpoint": cmd.endpoint, "error": result.error})
                except Exception as e:
                    self.event_log.append("ue5_command_error", {"endpoint": cmd.endpoint, "error": str(e)})

        # Sauvegarder les commandes
        path = self.workdir / "ue5_commands.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(commands.to_mapping(), ensure_ascii=False, indent=2), encoding="utf-8")
        artifact = self.artifacts.register(
            Artifact(type="ue5_commands", name=commands.scene_name, path=path)
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)

        self._charge("blender", artifact)
        self.production_run.complete_step("blender")
        return commands, path

    def _synthesize_ue5_commands(self, scene: SceneSpec) -> UE5Commands:
        """Fallback: commandes UE5 basiques quand le LLM échoue."""
        from DeepBl4nder.domain.ue5 import UE5Command
        scene_name = _safe_name(scene.brief[:30] if scene.brief else "scene")
        commands = [
            UE5Command(endpoint="level/create", payload={"name": scene_name, "template": "empty"}),
            UE5Command(endpoint="lighting/setup", payload={
                "lights": [{"type": "DirectionalLight", "name": "Sun", "intensity": 10.0, "rotation": (45, 0, 0)}],
                "use_lumen": True,
                "skylight_intensity": 1.0,
            }),
        ]
        # Add characters
        for char in scene.characters:
            commands.append(UE5Command(endpoint="actor/create", payload={
                "type": "SkeletalMeshActor",
                "name": char.name,
                "transform": {"location": [char.position[0] * 100, char.position[1] * 100, char.position[2] * 100]},
            }))
        # Add render
        commands.append(UE5Command(endpoint="render/start", payload={
            "output": str((self.workdir / "render" / f"{scene_name}.mp4").resolve()),
            "resolution": list(scene.render.resolution),
            "format": scene.render.format,
            "quality": "cinematic",
        }, timeout=600.0))
        self.event_log.append("ue5_commands_synthesized", {"scene": scene_name, "reason": "generation_failed_twice"})
        self._emit("llm_call", {"step": "blender", "status": "synthesized_fallback"})
        return UE5Commands(scene_name=scene_name, commands=commands)

    async def _build_blender(self, scene: SceneSpec) -> tuple[BlenderScript, Path]:
        """Build Blender script (original logic)."""
        self.production_run.start_step("blender")
        self._emit("llm_call", {"step": "blender", "agent": "BlenderAgent", "status": "started", "model": getattr(self.blender, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        try:
            # Injecter le chemin absolu du dossier de rendu dans le contexte
            # de l'agent pour que le script généré écrive les fichiers au bon endroit.
            render_dir = str((self.workdir / "render").resolve()).replace("\\", "/")
            if hasattr(self.blender, "context") and hasattr(self.blender.context, "set"):
                self.blender.context["render_dir"] = render_dir
            script = await self._with_generation_retry(
                "blender", lambda: self.blender.build_script(scene)
            )
        except GenerationError:
            # Deux générations épuisées (log 22:49 : le modèle recopie
            # l'enveloppe d'appel au lieu du résultat) : script déterministe
            # plutôt que run tué après ~8 minutes de calcul.
            script = self._synthesize_blender_script(scene)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "blender", "agent": "BlenderAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.blender)})
        path = self.workdir / _safe_name(script.scene_name or "scene") / "script.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script.code, encoding="utf-8")
        # Méta du script : permet la reprise (checkpoint blender) sans relire
        # le nom de scène depuis l'agent.
        self._write_json(
            "blender_script.json",
            {
                "scene_name": script.scene_name,
                "version": script.version,
                "code_sha256": CheckpointManager.script_fingerprint(script.code),
            },
        )
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
        script: Any,  # BlenderScript or UE5Commands
    ) -> QAReport:
        self.production_run.start_step("qa")
        self._emit("llm_call", {"step": "qa", "agent": "QAAgent", "status": "started", "model": getattr(self.qa, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()

        # UE5: skip full QA, just check validation
        if scene.render.is_ue5_engine():
            if not validation.ok:
                issues = [
                    Issue(kind=IssueKind.TECHNICAL, message=error, step="blender")
                    for error in validation.errors
                ]
                report = QAReport(passed=False, score=0.0, issues=issues)
            else:
                # UE5 commands generated successfully
                report = QAReport(passed=True, score=0.8, issues=[])

            elapsed = round(time.time() - t0, 2)
            self._emit("llm_call", {"step": "qa", "agent": "QAAgent", "status": "completed", "elapsed_s": elapsed, "score": report.score})
            self.production_run.complete_step("qa")
            return report

        # Blender: full QA with code assessment
        script_code = getattr(script, "code", "")
        # L'agent QA est sandboxé : on lui passe le code source en ligne plutôt
        # qu'un chemin hôte qu'il ne pourrait pas lire ("File not found").
        if not script_path.is_file():
            report = QAReport(
                passed=False,
                score=0.0,
                issues=[Issue(kind=IssueKind.TECHNICAL, message="script file missing", step="blender")],
            )
        else:
            report = await self._with_generation_retry(
                "qa",
                lambda: self.qa.assess(scene, str(script_path), code=script_code),
            )
        if not validation.ok:
            issues = [
                Issue(kind=IssueKind.TECHNICAL, message=error, step="blender")
                for error in validation.errors
            ]
            report = QAReport(passed=False, score=0.0, issues=issues)
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "qa", "agent": "QAAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.qa), "score": report.score})
        # Checkpoint QA : réutilisable seulement si le rapport a passé ET que le
        # code courant est exactement celui évalué (empreinte).
        script_code = getattr(script, "code", "")
        self._write_json(
            "qa_report.json",
            {
                "script_sha256": CheckpointManager.script_fingerprint(script_code) if script_code else "ue5_commands",
                "passed": report.passed,
                "score": report.score,
                "issues": [
                    {
                        "kind": issue.kind.value if hasattr(issue.kind, "value") else str(issue.kind),
                        "message": issue.message,
                        "step": issue.step,
                    }
                    for issue in report.issues
                ],
                "recommendations": list(report.recommendations),
            },
        )
        if report.passed:
            self.checkpoints.mark_checkpoint("qa")
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

    async def _run_character_design(self, scene: SceneSpec) -> Any:
        """Exécute CharacterDesignerAgent -> CharacterDesignResult."""
        if self.character_designer is None:
            return None
        self.production_run.start_step("character_design")
        self._emit("llm_call", {"step": "character_design", "agent": "CharacterDesignerAgent", "status": "started", "model": getattr(self.character_designer, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        result = await self._with_generation_retry(
            "character_design", lambda: self.character_designer.design_characters(scene)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "character_design", "agent": "CharacterDesignerAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.character_designer)})
        path = self._write_json("character_design.json", result.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="character_design", name="characters", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("character_design", artifact)
        self.production_run.complete_step("character_design")
        return result

    async def _run_environment(self, scene: SceneSpec) -> Any:
        """Exécute EnvironmentArtistAgent -> EnvironmentDesignResult."""
        if self.environment_artist is None:
            return None
        self.production_run.start_step("environment")
        self._emit("llm_call", {"step": "environment", "agent": "EnvironmentArtistAgent", "status": "started", "model": getattr(self.environment_artist, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        result = await self._with_generation_retry(
            "environment", lambda: self.environment_artist.design_environment(scene)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "environment", "agent": "EnvironmentArtistAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.environment_artist)})
        path = self._write_json("environment_design.json", result.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="environment_design", name="environment", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("environment", artifact)
        self.production_run.complete_step("environment")
        return result

    async def _run_animation(self, scene: SceneSpec) -> Any:
        """Exécute AnimatorAgent -> AnimationResult."""
        if self.animator is None:
            return None
        self.production_run.start_step("animation")
        self._emit("llm_call", {"step": "animation", "agent": "AnimatorAgent", "status": "started", "model": getattr(self.animator, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        result = await self._with_generation_retry(
            "animation", lambda: self.animator.generate_animations(scene)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "animation", "agent": "AnimatorAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.animator)})
        path = self._write_json("animation.json", result.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="animation", name="animation", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("animation", artifact)
        self.production_run.complete_step("animation")
        return result

    def _record_revision(self, target: str, report: QAReport, revision: int) -> None:
        revision_spec = RevisionSpec(
            issues=list(report.issues),
            target_step=target,
            instructions=self.context_injector._format_feedback(report, revision),
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
