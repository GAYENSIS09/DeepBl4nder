"""ProductionRun : corrélation production/agent, étapes et reprise."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from deepblender.production.events import APPROVAL_EVENTS, STEP_EVENTS, EventLog

RunStatus = Literal["created", "planned", "running", "awaiting_approval", "completed", "revision", "blocked"]


@dataclass
class ProductionStep:
    """Une étape du run, reliée à un artifact et à un run agent si pertinent."""

    name: str
    status: str = "pending"
    agent_run_id: str = ""
    artifact_id: str = ""
    started_at: float = field(default_factory=time.time)


@dataclass
class ProductionRun:
    """Un run de production, porteur de l'identité de corrélation (Roadmap C §7)."""

    project_id: str
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    status: RunStatus = "created"
    steps: dict[str, ProductionStep] = field(default_factory=dict)
    correlation: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    log: EventLog | None = None

    def add_step(self, step: ProductionStep) -> ProductionStep:
        self.steps[step.name] = step
        return step

    def mark_step(self, name: str, status: str) -> None:
        if name in self.steps:
            self.steps[name].status = status

    def start_step(self, name: str) -> None:
        self.mark_step(name, "running")
        if self.log:
            self.log.append("step_started", {"step": name})

    def complete_step(self, name: str) -> None:
        self.mark_step(name, "completed")
        if self.log:
            self.log.append("step_completed", {"step": name})

    def fail_step(self, name: str) -> None:
        self.mark_step(name, "failed")
        if self.log:
            self.log.append("step_failed", {"step": name})

    def request_approval(self, name: str) -> None:
        """Human-in-the-loop : bloque l'étape en attente d'une décision humaine."""
        self.mark_step(name, "awaiting_approval")
        self.status = "awaiting_approval"
        if self.log:
            self.log.append("approval_requested", {"step": name})

    def approve(self, name: str) -> None:
        self.mark_step(name, "approved")
        if self.status == "awaiting_approval":
            self.status = "running"
        if self.log:
            self.log.append("approval_granted", {"step": name})

    def reject(self, name: str, reason: str) -> None:
        self.mark_step(name, "rejected")
        self.status = "revision"
        if self.log:
            self.log.append("approval_rejected", {"step": name, "reason": reason})

    def step(self, name: str) -> ProductionStep | None:
        return self.steps.get(name)

    def pending_steps(self) -> list[str]:
        return [name for name, step in self.steps.items() if step.status == "pending"]

    @classmethod
    def recover(cls, project_id: str, log: EventLog) -> ProductionRun:
        """Reconstruit un run depuis le journal et marque le travail non consommé.

        Rejeu des événements non consommés : les étapes avec un événement
        `step_started` mais aucun événement terminal (`step_completed` /
        `step_failed`) repassent `pending` pour être resoumises après crash.
        Une approbation demandée sans décision (`approval_granted` /
        `approval_rejected`) reste en attente humaine.
        """
        run = cls(project_id=project_id, log=log)
        states: dict[str, str] = {}
        pending_approval: dict[str, bool] = {}
        for event in log.load():
            if event.kind == "run_started":
                run.status = "running"
            elif event.kind == "run_completed":
                run.status = "completed"
            elif event.kind == "run_blocked":
                run.status = "blocked"
            elif event.kind in STEP_EVENTS:
                name = event.payload.get("step", "")
                if not name:
                    continue
                if name not in run.steps:
                    run.add_step(ProductionStep(name=name))
                states[name] = {
                    "step_started": "pending",
                    "step_completed": "completed",
                    "step_failed": "failed",
                }[event.kind]
            elif event.kind in APPROVAL_EVENTS:
                name = event.payload.get("step", "")
                if not name:
                    continue
                if name not in run.steps:
                    run.add_step(ProductionStep(name=name))
                if event.kind == "approval_requested":
                    states[name] = "awaiting_approval"
                    pending_approval[name] = True
                elif event.kind == "approval_granted":
                    states[name] = "approved"
                    pending_approval[name] = False
                else:
                    states[name] = "rejected"
                    pending_approval[name] = False
        for name, status in states.items():
            run.mark_step(name, status)
        if any(pending_approval.values()):
            run.status = "awaiting_approval"
        elif run.status not in ("completed", "blocked"):
            run.status = "running"
        return run

    def snapshot(self) -> dict[str, object]:
        """Point de reprise minimal : état persistant après crash (Roadmap C §35)."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "correlation": self.correlation,
            "steps": {name: step.status for name, step in self.steps.items()},
        }
