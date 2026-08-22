"""Exécution du PipelineRunner branchée à l'API SaaS.

`run_production` lance le pipeline en tâche de fond : elle ouvre ses propres
sessions (le contexte de requête FastAPI est fermé), tient la ligne `Production`
à jour (statut, étape courante, progression, coût, erreur) et publie chaque
transition sur le bus asynchrone pour le flux SSE.

Les agents sont construits par `build_agents` (patchable dans les tests) :
par défaut ce sont les vrais agents NOOA sur le LLM configuré (ou FakeLLM via
`build_llm(fake=True)`).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from deepblender.agents import (
    AudioAgent,
    BlenderAgent,
    CompositingAgent,
    DirectorAgent,
    LocalizationAgent,
    QAAgent,
    StoryAgent,
    StoryboardAgent,
)
from deepblender.api.models import Production
from deepblender.domain.project import Brief
from deepblender.llm import build_llm
from deepblender.production.budget import BudgetTracker
from deepblender.production.runner import PipelineRunner

EventHook = Callable[[str, dict[str, Any]], None]

# Coûts estimés par étape (USD) — basés sur les prix LLM typiques
_STEP_COSTS: dict[str, float] = {
    "director": 0.005,    # ~2k tokens input + 1k output
    "blender": 0.010,     # ~4k tokens input + 2k output
    "qa": 0.003,          # ~1k tokens
    "render": 0.0,        # GPU local, pas de coût LLM
    "audio": 0.005,       # ~2k tokens
    "compositing": 0.003, # ~1k tokens
    "localization": 0.008,# ~3k tokens par langue
}


def _default_cost_hook(step: str) -> float:
    """Retourne le coût estimé pour une étape donnée."""
    return _STEP_COSTS.get(step, 0.001)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_agents() -> tuple[Any, Any, Any, Any, Any, Any, Any, Any]:
    """Construit les agents NOOA (story, storyboard, directeur, Blender, QA + post-production)."""
    llm = build_llm()
    return (
        StoryAgent(llm=llm),
        StoryboardAgent(llm=llm),
        DirectorAgent(llm=llm),
        BlenderAgent(llm=llm),
        QAAgent(llm=llm),
        AudioAgent(llm=llm),
        LocalizationAgent(llm=llm),
        CompositingAgent(llm=llm),
    )


class RunTracker:
    """Tient la base à jour et publie les événements pendant un run."""

    def __init__(
        self,
        *,
        production_id: str,
        total_steps: int,
        bus: Any,
        session_factory: Any,
    ) -> None:
        self._production_id = production_id
        self._total_steps = max(total_steps, 1)
        self._bus = bus
        self._session_factory = session_factory
        self._completed = 0

    def _apply(self, fields: dict[str, Any], *, bump_version: bool = False) -> None:
        session = self._session_factory()
        try:
            production = session.get(Production, self._production_id)
            if production is None:
                return
            for key, value in fields.items():
                setattr(production, key, value)
            if bump_version:
                production.version = (production.version or 1) + 1
            production.updated_at = _utcnow()
            session.commit()
        finally:
            session.close()

    def _add_cost(self, amount: float) -> None:
        session = self._session_factory()
        try:
            production = session.get(Production, self._production_id)
            if production is None:
                return
            production.cost = (production.cost or 0.0) + amount
            production.updated_at = _utcnow()
            session.commit()
        finally:
            session.close()

    def _publish(self, kind: str, payload: dict[str, Any]) -> None:
        if self._bus is None:
            return
        event: dict[str, Any] = {
            "type": kind,
            "production_id": self._production_id,
            "ts": time.time(),
            **payload,
        }
        self._bus.publish_nowait(event)

    def on_event(self, kind: str, payload: dict[str, Any]) -> None:
        """Relaye un événement du journal pipeline vers la DB et le bus."""
        now = _utcnow()
        if kind == "run_started":
            self._apply({"status": "running", "started_at": now})
        elif kind == "step_started":
            self._apply({"status": "running", "current_step": payload.get("step", "")})
        elif kind == "step_completed":
            self._completed += 1
            self._apply({"progress": min(1.0, self._completed / self._total_steps)})
        elif kind == "step_failed":
            self._apply(
                {
                    "status": "failed",
                    "error": f"step failed: {payload.get('step', '')}",
                    "finished_at": now,
                }
            )
        elif kind == "revision_requested":
            self._apply({"status": "revising"})
        elif kind == "cost_recorded":
            self._add_cost(float(payload.get("cost", 0.0)))
        elif kind == "run_completed":
            self._apply(
                {"status": "completed", "progress": 1.0, "finished_at": now, "error": ""},
                bump_version=True,
            )
        elif kind == "run_blocked":
            self._apply(
                {
                    "status": "blocked",
                    "finished_at": now,
                    "error": f"blocked at {payload.get('step', '?')} (révisions épuisées)",
                }
            )
        self._publish(kind, payload)

    def on_error(self, message: str) -> None:
        """Run interrompu par une exception : marque l'échec et le publie."""
        self._apply({"status": "failed", "error": message[:2000], "finished_at": _utcnow()})
        self._publish("run_failed", {"error": message})


async def run_production(
    *,
    production_id: str,
    project_id: str,
    brief: str,
    workdir: Path,
    bus: Any = None,
    session_factory: Any = None,
    budget_limit: float = 1.0,
    total_steps: int = 9,  # story + storyboard + director + blender + qa + render + audio + localization + compositing
    agents: tuple[Any, Any, Any, Any, Any, Any, Any, Any] | None = None,
) -> None:
    """Lance le pipeline en tâche de fond et tient DB + bus à jour."""
    story, storyboard, director, blender, qa, audio, localization, compositing = agents or build_agents()
    workdir.mkdir(parents=True, exist_ok=True)
    budget = BudgetTracker(budget=budget_limit, run_id=production_id)

    # Create Blender bridge for rendering (lazy import to avoid slow startup)
    from deepblender.blender.bridge import BlenderBridge
    blender_bridge = BlenderBridge()

    # Max render retries from env (default 2)
    import os
    max_render_retries = int(os.environ.get("DEEPBLENDER_MAX_RENDER_RETRIES", "2"))

    # Default total steps: story + storyboard + director + blender + qa + render + audio + localization + compositing = 9
    if total_steps == 7:
        total_steps = 9

    tracker = RunTracker(
        production_id=production_id,
        total_steps=total_steps,
        bus=bus,
        session_factory=session_factory,
    )
    runner = PipelineRunner(
        project_id=project_id,
        director=director,
        blender=blender,
        qa=qa,
        audio=audio,
        localization=localization,
        compositing=compositing,
        workdir=workdir,
        budget=budget,
        event_hook=tracker.on_event,
        blender_bridge=blender_bridge,
        cost_hook=_default_cost_hook,
        max_render_retries=max_render_retries,
        session_factory=session_factory,
        production_id=production_id,
        story=story,
        storyboard=storyboard,
    )
    try:
        await runner.run(Brief(text=brief))
    except Exception as exc:  # noqa: BLE001
        tracker.on_error(f"{type(exc).__name__}: {exc}")
