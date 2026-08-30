"""Embedded TUI API - direct access to production internals without HTTP.

Builds the real NOOA agents (`DeepBl4nder.api.pipeline.build_agents`), wires
them into the `EventBroker` live stream and runs `PipelineRunner` in-process.
No fake/mock mode: a missing LLM provider surfaces as a clean error the
console shows instead of a silent broken run.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from DeepBl4nder.artifacts.provenance import ProvenanceGraph
from DeepBl4nder.artifacts.registry import ArtifactRegistry, classify_artifact_type
from DeepBl4nder.bridges.blender.bridge import BlenderBridge
from DeepBl4nder.domain.project import Brief
from DeepBl4nder.plugins.registry import PluginRegistry
from DeepBl4nder.production.budget import BudgetAlert, BudgetTracker
from DeepBl4nder.production.events import EventLog
from DeepBl4nder.production.runs import ProductionRun, RunStatus
from DeepBl4nder.production.runner import PipelineRunner, RunOutcome
from DeepBl4nder.tui.event_bridge import EventBroker, StreamEvent, attach_agent_bridge

logger = logging.getLogger("DeepBl4nder.tui.embedded")

_AGENT_RUNNER_KEYS: list[str] = [
    "story",
    "storyboard",
    "director",
    "blender",
    "qa",
    "audio",
    "localization",
    "compositing",
    "character_designer",
    "animator",
    "environment_artist",
    "music_composer",
    "sound_designer",
    "review",
]


@dataclass
class EmbeddedProduction:
    """Lightweight production view for the TUI."""

    id: str
    name: str
    brief: str
    status: str
    current_step: str | None
    progress: float
    cost: float
    created_at: float
    updated_at: float
    workdir: Path
    resumable: bool = False
    checkpoint_steps: list[str] = field(default_factory=list)


@dataclass
class EmbeddedArtifact:
    """Lightweight artifact view for the TUI."""

    id: str
    type: str
    name: str
    path: Path
    size: int
    status: str
    created_at: float
    provenance_parents: list[str]


def _format_pipeline_event(kind: str, payload: dict[str, Any]) -> str:
    step = payload.get("step") or payload.get("agent") or ""
    cost = payload.get("cost")
    elapsed = payload.get("elapsed_s")
    if kind == "run_started":
        return "Production started"
    if kind in ("step_started", "step_completed", "step_failed"):
        return f"{kind.replace('step_', 'step ').replace('_', ' ')}: {step}"
    if kind == "llm_call":
        status = payload.get("status", "")
        if status == "started":
            return f"Calling LLM for {payload.get('agent', '')} ({payload.get('model', '')})"
        if status == "completed":
            tail = ", $%.4f" % cost if cost else ""
            tail = f"{tail}, {elapsed:.1f}s" if elapsed else tail
            return f"{payload.get('agent', '')} LLM done{tail}"
        return f"llm_call: {status}"
    if kind == "cost_recorded":
        return f"Cost recorded: ${float(cost or 0.0):.4f} ({step})"
    if kind == "revision_requested":
        return f"Revision requested for {step}"
    if kind == "approval_required":
        return f"Approval required at {step}"
    if kind == "render_started":
        return f"Render started: {step or payload.get('name', '')}"
    if kind == "render_completed":
        return f"Render completed: {payload.get('output') or step}"
    if kind == "scene_inspected":
        return f"Scene inspected ({payload.get('objects', 0)} objects)"
    if kind == "run_completed":
        return "Production completed"
    if kind == "run_blocked":
        return "Production blocked (revisions exhausted)"
    if kind == "run_failed":
        return f"Production failed: {payload.get('error', '')}"
    static = " ".join(f"{k}={v}" for k, v in payload.items() if k != "step")
    return f"{kind.replace('_', ' ')} {static}".strip()


class EmbeddedAPI:
    """Direct internal API for the TUI - no HTTP layer, real agents."""

    def __init__(
        self,
        data_dir: str | Path = "data",
        *,
        blender_bridge: BlenderBridge | None = None,
        enable_cache: bool = True,
        max_revisions: int = 1,
        budget: float = 1.0,
    ):
        budget = float(os.environ.get("DeepBl4nder_BUDGET", budget))
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.blender_bridge = blender_bridge or BlenderBridge()
        self.enable_cache = enable_cache
        self.max_revisions = max_revisions

        self.plugins = PluginRegistry()
        self.plugins.on_plugin = self._plugin_event
        self.artifacts = ArtifactRegistry()
        self.provenance = ProvenanceGraph()
        self.budget = BudgetTracker(budget=budget)

        self.broker = EventBroker()

        self._runner: PipelineRunner | None = None
        self._run_task: asyncio.Task | None = None
        self._current_production: EmbeddedProduction | None = None
        self._agents: dict[str, Any] = {}
        self._agents_ready = False
        self._agent_error: Exception | None = None
        self._building_exception: Exception | None = None

        self.budget.subscribe(self._on_budget_alert)

    # ========== Agents ==========

    def _production_id(self) -> str | None:
        return self._current_production.id if self._current_production else None

    def _publish(
        self,
        kind: str,
        content: str,
        *,
        actor: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.broker.publish(
            StreamEvent(
                seq=0,
                ts=time.time(),
                kind=kind,
                actor=actor,
                content=content,
                meta=meta or {},
                production_id=self._production_id(),
            )
        )

    def _on_budget_alert(self, alert: BudgetAlert) -> None:
        self._publish(
            "budget_alert",
            f"Budget exceeded by ${alert.overshoot:.2f} - stopping (limit ${alert.budget:.2f})",
            meta={
                "budget": alert.budget,
                "total": alert.total,
                "overshoot": alert.overshoot,
                "run_id": alert.run_id,
            },
        )

    def _skills_event(self, actor: str, names: list[str]) -> None:
        label = ", ".join(names) if names else "none"
        self._publish(
            "skills_loaded",
            f"skills: {label}",
            actor=actor,
            meta={"skills": names, "actor": actor},
        )

    def _runtime_skill_sink(self, actor: str) -> Callable[[list[str]], None]:
        def sink(names: list[str]) -> None:
            if names:
                self._skills_event(actor, names)

        return sink

    def _plugin_event(self, name: str, method: str) -> None:
        self._publish(
            "plugin_used",
            f"plugin: {name}.{method}",
            meta={"plugin": name, "method": method},
        )

    def create_agents(self) -> dict[str, Any]:
        """Build the full NOOA agent crew and attach the live event bridge."""
        if self._agents_ready:
            return self._agents
        if self._building_exception:
            raise self._building_exception

        from DeepBl4nder.api.pipeline import build_agents

        try:
            built = build_agents()
        except Exception as exc:  # noqa: BLE001
            self._building_exception = exc
            self._agent_error = exc
            raise

        agents = dict(zip(_AGENT_RUNNER_KEYS, built, strict=True))
        ue5 = self._try_build_ue5()
        if ue5 is not None:
            agents["ue5"] = ue5

        for slug, agent in agents.items():
            attach_agent_bridge(
                agent=agent,
                actor=slug,
                broker=self.broker,
                production_id=self._production_id,
            )

        for slug, agent in agents.items():
            blocks = getattr(agent, "_agent_context_blocks", None) or {}
            names: list[str] = []
            if "available_skills" in blocks:
                try:
                    count = len(agent.get_skill_registry().summaries())
                except Exception:  # noqa: BLE001
                    count = 0
                names.append(f"<{count} core summaries>" if count else "core summaries")
            for key in blocks:
                if isinstance(key, str) and key.startswith("skill_"):
                    names.append(key[len("skill_"):])
            self._skills_event(slug, names)
            setattr(agent, "_skill_sink", self._runtime_skill_sink(slug))

        self._agents = agents
        self._agents_ready = True
        logger.info("Built %d agents", len(agents))
        return agents

    def _try_build_ue5(self) -> Any | None:
        try:
            from DeepBl4nder.agents import UE5Agent
            from DeepBl4nder.llm import build_llm

            return UE5Agent(llm=build_llm())
        except Exception as exc:  # noqa: BLE001
            logger.debug("UE5 agent unavailable: %s", exc)
            return None

    @property
    def agent_error(self) -> Exception | None:
        return self._agent_error

    # ========== Production Management ==========

    def list_productions(self) -> list[EmbeddedProduction]:
        productions: list[EmbeddedProduction] = []
        runs_dir = self.data_dir / "runs"
        if not runs_dir.exists():
            return productions
        for prod_dir in runs_dir.iterdir():
            if not prod_dir.is_dir():
                continue
            prod = self._load_production_state(prod_dir)
            if prod:
                productions.append(prod)
        return sorted(productions, key=lambda p: p.updated_at, reverse=True)

    def _load_production_state(self, prod_dir: Path) -> EmbeddedProduction | None:
        event_log_path = prod_dir / "events.jsonl"
        if not event_log_path.exists():
            return None

        event_log = EventLog(event_log_path)
        events = event_log.load()

        try:
            run = ProductionRun.recover("unknown", event_log)
        except Exception:  # noqa: BLE001
            run = None

        status = run.status if run else RunStatus.CREATED
        current_step = None
        completed = 0
        total = len(run.steps) if run and run.steps else 0
        if run:
            for step in run.steps.values():
                if step.status == "running":
                    current_step = step.name
                elif step.status == "completed":
                    completed += 1
        progress = completed / total if total > 0 else 0.0

        brief = "Unknown"
        cost = 0.0
        for event in events:
            if event.kind == "run_completed":
                progress = 1.0
            if event.kind == "director_completed" and "brief" in event.payload:
                brief = str(event.payload.get("brief", "Unknown"))[:200]
            if event.kind == "cost_recorded":
                cost += float(event.payload.get("cost", 0.0))

        checkpoint_steps = self._checkpoint_steps(prod_dir)
        resumable = bool(checkpoint_steps) and status not in ("completed", "blocked")

        created = run.created_at if run is not None and run.created_at else prod_dir.stat().st_ctime
        updated = events[-1].ts if events else created

        return EmbeddedProduction(
            id=prod_dir.name,
            name=prod_dir.name,
            brief=brief,
            status=status,
            current_step=current_step,
            progress=progress,
            cost=cost,
            created_at=created,
            updated_at=updated,
            workdir=prod_dir,
            resumable=resumable,
            checkpoint_steps=checkpoint_steps,
        )

    @staticmethod
    def _checkpoint_steps(prod_dir: Path) -> list[str]:
        """Étapes enregistrées comme reprenables dans ``run_state.json``."""
        state_path = prod_dir / "run_state.json"
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        steps = data.get("steps", []) if isinstance(data, dict) else []
        return sorted(s for s in steps if isinstance(s, str))

    def get_production(self, production_id: str) -> EmbeddedProduction | None:
        return self._load_production_state(self.data_dir / "runs" / production_id)

    def create_production(self, name: str, brief: str, project_id: str = "default") -> EmbeddedProduction:
        prod_id = uuid4().hex[:12]
        workdir = self.data_dir / "runs" / prod_id
        workdir.mkdir(parents=True, exist_ok=True)

        event_log = EventLog(workdir / "events.jsonl")
        event_log.append("run_started", {"project_id": project_id, "name": name, "brief": brief})

        prod = EmbeddedProduction(
            id=prod_id,
            name=name,
            brief=brief,
            status="created",
            current_step=None,
            progress=0.0,
            cost=0.0,
            created_at=time.time(),
            updated_at=time.time(),
            workdir=workdir,
        )
        self._current_production = prod
        return prod

    def current_production(self) -> EmbeddedProduction | None:
        return self._current_production

    def _runner_kwargs(self, prod: EmbeddedProduction, event_hook: Callable[[str, dict[str, Any]], None]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "project_id": "embedded",
            "director": self._agents.get("director"),
            "blender": self._agents.get("blender"),
            "qa": self._agents.get("qa"),
            "workdir": prod.workdir,
            "plugins": self.plugins,
            "artifacts": self.artifacts,
            "provenance": self.provenance,
            "budget": self.budget,
            "event_hook": event_hook,
            "max_revisions": self.max_revisions,
            "enable_cache": self.enable_cache,
            "blender_bridge": self.blender_bridge,
            "session_factory": None,
            "production_id": prod.id,
        }
        for key in _AGENT_RUNNER_KEYS:
            if key in self._agents:
                kwargs[key] = self._agents[key]
        if "ue5" in self._agents:
            kwargs["ue5"] = self._agents["ue5"]
        return kwargs

    async def run_production(self, production_id: str) -> RunOutcome:
        prod = self.get_production(production_id)
        if prod is None:
            raise ValueError(f"Production not found: {production_id}")

        if self._agent_error:
            raise RuntimeError(f"LLM provider not configured: {self._agent_error}")

        if not self._agents_ready:
            try:
                self.create_agents()
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"LLM provider not configured: {exc}") from exc

        self._current_production = prod
        self.budget.reset_alert()

        def event_hook(kind: str, payload: dict[str, Any]) -> None:
            content = _format_pipeline_event(kind, payload)
            meta = dict(payload)
            actor = payload.get("agent")
            if isinstance(actor, str) and actor.endswith("Agent"):
                actor = actor[: -len("Agent")].lower()
            if actor not in self._agents:
                actor = None
            self._publish(kind, content, actor=actor, meta=meta)

        runner = PipelineRunner(**self._runner_kwargs(prod, event_hook=event_hook))
        self._runner = runner
        brief_obj = Brief(text=prod.brief, id=prod.id)

        try:
            self._publish("run_started", f"Running production {prod.name} (brief: {prod.brief[:80]})")
            task = asyncio.create_task(runner.run(brief_obj))
            self._run_task = task
            return await task
        finally:
            if self._run_task is task:
                self._run_task = None
            self._runner = None

    def cancel_production(self, production_id: str | None = None) -> None:
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
        self._publish("run_cancelled", "Run cancelled by user")

    def fail_production(self, production_id: str, message: str) -> None:
        """Marque un run comme échoué dans events.jsonl (statut persistant)."""
        if self.get_production(production_id) is None:
            return
        try:
            event_log = EventLog(self.data_dir / "runs" / production_id / "events.jsonl")
            event_log.append("run_failed", {"error": message[:2000]})
        except OSError:
            pass

    # ========== Real-time Events ==========

    async def subscribe_events(self, production_id: str | None = None) -> asyncio.Queue[StreamEvent]:
        """Subscribe to the live agent stream, preloaded with history."""
        return await self.broker.subscribe(production_id)

    def unsubscribe_events(self, queue: asyncio.Queue[StreamEvent]) -> None:
        """Stop delivering broker events to this queue (screen leave)."""
        self.broker.unsubscribe(queue)

    # ========== Artifacts ==========

    def list_artifacts(self, production_id: str) -> list[EmbeddedArtifact]:
        workdir = self.data_dir / "runs" / production_id
        if not workdir.exists():
            return []

        artifacts = []
        for art_file in sorted(workdir.rglob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if not art_file.is_file() or art_file.suffix in (".jsonl", ".log"):
                continue
            rel_path = art_file.relative_to(workdir)
            stat = art_file.stat()

            artifacts.append(
                EmbeddedArtifact(
                    id=art_file.stem,
                    type=classify_artifact_type(art_file.name),
                    name=art_file.name,
                    path=rel_path,
                    size=stat.st_size,
                    status="completed",
                    created_at=stat.st_mtime,
                    provenance_parents=[],
                )
            )

        return sorted(artifacts, key=lambda a: a.created_at, reverse=True)

    def get_qa_report(self, production_id: str) -> dict[str, Any] | None:
        """Rapport QA structuré depuis ``qa_report.json`` (ou ``None``)."""
        path = self.data_dir / "runs" / production_id / "qa_report.json"
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        issues = data.get("issues", [])
        recommendations = data.get("recommendations", [])
        return {
            "passed": bool(data.get("passed")),
            "score": float(data.get("score", 0.0)),
            "issues": [
                it if isinstance(it, dict) else {"kind": "technical", "message": str(it), "step": ""}
                for it in (issues if isinstance(issues, list) else [])
            ],
            "recommendations": [str(r) for r in recommendations] if isinstance(recommendations, list) else [],
        }

    def download_artifact(self, production_id: str, rel_path: str) -> bytes:
        return self._resolved_artifact_path(production_id, rel_path).read_bytes()

    def artifact_abs_path(self, production_id: str, rel_path: str) -> Path:
        return self._resolved_artifact_path(production_id, rel_path)

    def _resolved_artifact_path(self, production_id: str, rel_path: str) -> Path:
        workdir = (self.data_dir / "runs" / production_id).resolve()
        full_path = (workdir / rel_path).resolve()
        if workdir not in full_path.parents and full_path != workdir:
            raise ValueError("Invalid path")
        return full_path

    # ========== Status ==========

    def get_agent_status(self) -> dict[str, Any]:
        return {
            name: {
                "type": type(agent).__name__,
                "model": getattr(agent, "_get_model_id", lambda: "unknown")(),
                "available": agent is not None,
            }
            for name, agent in self._agents.items()
        }

    def router_stats(self) -> dict[str, Any]:
        """Statistiques du routeur LLM partagé (santé par fournisseur)."""
        from DeepBl4nder.llm import routing_stats

        return routing_stats()


# Global instance for the TUI
_embedded_api: EmbeddedAPI | None = None


def get_embedded_api(**kwargs) -> EmbeddedAPI:
    global _embedded_api
    if _embedded_api is None:
        _embedded_api = EmbeddedAPI(**kwargs)
    return _embedded_api