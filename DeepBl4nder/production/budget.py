"""Budget de production : suivi des coûts et alerte de dépassement.

Chaque ProductionRun suit coût LLM, coût render, coût storage, coût API
externe, total, budget et budget restant (Roadmap C §19). L'alerte de
dépassement est émise à la transition budget franchi (temps réel < 30 s) :
`subscribe` reçoit un `BudgetAlert` unique par passage au-dessus du seuil.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class BudgetAlert:
    """Émis quand le budget est franchi (une seule fois par dépassement)."""

    run_id: str
    budget: float
    total: float
    overshoot: float


@dataclass
class BudgetTracker:
    """Suivi des couts d'un run avec politique d'arret et alerte."""

    budget: float
    llm: float = 0.0
    render: float = 0.0
    storage: float = 0.0
    external: float = 0.0
    run_id: str = ""
    _listeners: list[Callable[[BudgetAlert], None]] = field(init=False, default_factory=list)
    _alerted: bool = field(init=False, default=False)

    def subscribe(self, listener: Callable[[BudgetAlert], None]) -> None:
        self._listeners.append(listener)

    def reset_alert(self) -> None:
        self._alerted = False

    def _charge(self, cost: float) -> None:
        if self.over_budget() and not self._alerted:
            self._alerted = True
            alert = BudgetAlert(
                run_id=self.run_id,
                budget=self.budget,
                total=self.total,
                overshoot=self.total - self.budget,
            )
            for listener in self._listeners:
                listener(alert)

    def add_llm(self, cost: float) -> None:
        self.llm += cost
        self._charge(cost)

    def add_render(self, cost: float) -> None:
        self.render += cost
        self._charge(cost)

    def add_storage(self, cost: float) -> None:
        self.storage += cost
        self._charge(cost)

    def add_external(self, cost: float) -> None:
        self.external += cost
        self._charge(cost)

    @property
    def total(self) -> float:
        return self.llm + self.render + self.storage + self.external

    @property
    def remaining(self) -> float:
        return round(max(0.0, self.budget - self.total), 10)

    def over_budget(self) -> bool:
        return self.total > self.budget

    def report(self) -> dict[str, float]:
        return {
            "llm": self.llm,
            "render": self.render,
            "storage": self.storage,
            "external": self.external,
            "total": self.total,
            "budget": self.budget,
            "remaining": self.remaining,
        }
