"""Console screen - the opencode-style main view of the DeepBl4nder TUI.

Top: brief input + engine picker + run controls.
Middle: live agent stream (reasoning, code, tool calls, steps) on the left,
production status + artifacts shortcut on the right.
Bottom: status bar with real-time cost, budget, provider and step.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar, Static
from textual.worker import Worker, WorkerState

from DeepBl4nder.tui import theme
from DeepBl4nder.tui.embedded_api import EmbeddedAPI, EmbeddedProduction
from DeepBl4nder.tui.event_bridge import StreamEvent
from DeepBl4nder.tui.screens.base import BaseScreen
from DeepBl4nder.tui.widgets.agent_stream import AgentStream
from DeepBl4nder.tui.widgets.status_bar import StatusBar
from DeepBl4nder.tui.widgets.task_bar import TaskBar

logger = logging.getLogger("DeepBl4nder.tui.console")


def _first_error_line(message: str) -> str:
    """Extrait une ligne lisible d'une exception multi-lignes (fournisseurs LLM...)."""
    for line in message.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:240] + ("…" if len(stripped) > 240 else "")
    return message[:240]


class SidePanel(Widget):
    """Right panel: production status, budget and the LLM provider/model in use."""

    def __init__(self, *, id: str = "side-panel") -> None:
        super().__init__(id=id)
        self._prod_name = None
        self._prod_status = None
        self._progress = None
        self._budget = None
        self._llm = None

    def compose(self) -> ComposeResult:
        with Vertical(id="side-panel-root"):
            yield Static("Production", id="panel-title")
            yield Label("-", id="panel-prod-name")
            yield Label("-", id="panel-prod-status")
            yield ProgressBar(id="panel-progress", show_percentage=True)
            yield Static("Budget breakdown", id="panel-budget-title")
            yield Static("-", id="panel-budget", markup=True)
            yield Static("LLM in use", id="panel-llm-title")
            yield Static("-", id="panel-llm", markup=True)

    def on_mount(self) -> None:
        self._prod_name = self.query_one("#panel-prod-name", Label)
        self._prod_status = self.query_one("#panel-prod-status", Label)
        self._progress = self.query_one("#panel-progress", ProgressBar)
        self._budget = self.query_one("#panel-budget", Static)
        self._llm = self.query_one("#panel-llm", Static)

    def update_production(self, prod: EmbeddedProduction | None) -> None:
        if prod is None:
            self._prod_name.update("-")
            self._prod_status.update("-")
            self._progress.progress = 0.0
            return
        self._prod_name.update(prod.name)
        suffix = f" · resume({len(prod.checkpoint_steps)})" if prod.resumable else ""
        self._prod_status.update(f"[{prod.status}]{suffix} {prod.current_step or 'waiting'}")
        self._prod_status.styles.color = (
            theme.SUCCESS if prod.status in ("completed", "running")
            else theme.WARNING if prod.status in ("revising", "blocked")
            else theme.TEXT_MUTED
        )
        self._progress.progress = min(1.0, max(0.0, prod.progress or 0.0))

    def update_budget(self, report: dict) -> None:
        if not report:
            self._budget.update("-")
            return
        line = (
            f"LLM [b]${report.get('llm', 0.0):.3f}[/b] render ${report.get('render', 0.0):.3f} "
            f"storage ${report.get('storage', 0.0):.3f} external ${report.get('external', 0.0):.3f}"
        )
        total = report.get("total", 0.0)
        limit = report.get("budget", 0.0)
        self._budget.update(f"{line}\nTotal [b]${total:.3f}[/b] / ${limit:.3f} (${report.get('remaining', 0.0):.3f} left)")
        self._budget.styles.color = theme.WARNING if total > limit * 0.8 else theme.TEXT_MUTED

    def update_llm(self, provider_line: str, models: list[str]) -> None:
        if not provider_line.strip() and not models:
            self._llm.update("[dim]-[/]")
            return
        lines = []
        if provider_line.strip():
            lines.append(f"router: [b]{provider_line}[/b]")
        if models:
            lines.append(f"model: [b]{', '.join(models[:2])}[/b]")
        elif provider_line.strip():
            # Routeur actif mais aucun vainqueur réel : on ne fabrique pas un
            # faux modèle statique — on montre l'état réel (attente/échec).
            lines.append("model: [i](no reply yet)[/i]")
        self._llm.update("\n".join(lines))


class ConsoleScreen(BaseScreen):
    """Main console: brief in, live agent reasoning stream out."""

    BINDINGS = [
        Binding("v", "event_detail", "Detail", show=True),
        Binding("c", "copy_stream", "Copy", show=True),
    ]

    def __init__(self, api: EmbeddedAPI):
        super().__init__(api, name="console")
        self._run_worker = None
        self._queue: asyncio.Queue[StreamEvent] | None = None
        self._pump: asyncio.Task | None = None
        self._current: EmbeddedProduction | None = None
        self._cost = 0.0
        self._event_ring: deque[StreamEvent] = deque(maxlen=300)
        self._run_error: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="console-root"):
            yield TaskBar(id="task-bar")
            with Horizontal(id="console-split"):
                yield AgentStream(id="agent-stream")
                yield SidePanel(id="side-panel")
            yield StatusBar(id="status-bar")

    # ========== lifecycle ==========

    def on_mount(self) -> None:
        status_bar = self.query_one(StatusBar)
        status_bar.set_budget(self.api.budget.budget)
        self._pump = asyncio.create_task(self._pump_loop())
        self.run_worker(self._bootstrap_agents(), name="bootstrap-agents", exclusive=True)

    def on_resize(self) -> None:
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        wide = self.size.width >= 104
        self.query_one(SidePanel).display = wide
        self.query_one("#taskbar-controls").display = self.size.width >= 64

    async def _bootstrap_agents(self) -> None:
        try:
            agents = self.api.create_agents()
        except Exception as exc:  # noqa: BLE001
            self.stream.write_line(f"Agent crew unavailable: {exc}", theme.ERROR)
            self.notify(f"No LLM provider configured: {exc}", severity="error")
            self.query_one(StatusBar).set_provider("no provider")
            return
        self.stream.write_line(f"Agent crew ready - {len(agents)} agents wired to the live stream", theme.SUCCESS)
        stats = self.api.router_stats()
        pool = stats.get("pool") or []
        if pool:
            self.stream.write_line(f"LLM router ({stats.get('rotation', '?')}): {', '.join(pool)}", theme.TEXT_MUTED)
        else:
            self.stream.write_line("LLM router not initialized yet (no provider configured?)", theme.WARNING)
        self._refresh_provider_label()

    async def _pump_loop(self) -> None:
        self._queue = await self.api.subscribe_events(None)
        while True:
            try:
                event = await self._queue.get()
            except asyncio.CancelledError:
                break
            try:
                self._handle_event(event)
            except Exception as exc:  # noqa: BLE001 - stream must never die
                self.stream.write_line(f"skipped bad event {event.kind}: {exc}", theme.ERROR)
                logger.exception("Failed to handle stream event %s", event.kind)

    def on_unmount(self) -> None:
        if self._pump is not None:
            self._pump.cancel()
        if self._queue is not None:
            self.api.unsubscribe_events(self._queue)

    # ========== run controls ==========

    @property
    def task_bar(self) -> TaskBar:
        return self.query_one(TaskBar)

    @on(Button.Pressed, "#btn-run")
    def _on_run(self) -> None:
        brief = self.task_bar.brief
        if not brief:
            self.notify("Describe your film idea first", severity="warning")
            return
        engine = self.task_bar.engine
        full_brief = f"[Engine: {engine}]\n{brief}" if engine != "blender" else brief

        if self.api.agent_error is not None:
            self._stream_fail(f"No LLM provider available: {self.api.agent_error}")
            self.notify("No LLM provider configured - set OPENAI_API_KEY or your provider's key", severity="error")
            return

        try:
            prod = self.api.create_production(name=f"production-{datetime.now().strftime('%H%M%S')}", brief=full_brief)
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Failed to create production: {exc}", severity="error")
            return

        self._current = prod
        self.stream.clear_stream()
        self.side_panel.update_production(prod)
        self.side_panel.update_budget(self.api.budget.report())
        task_bar = self.task_bar
        task_bar.set_running(True)
        status_bar = self.query_one(StatusBar)
        status_bar.set_running(True)
        status_bar.set_step("booting agents")
        self.stream.write_line("Starting pipeline...", theme.ACCENT)

        self._run_worker = self.run_worker(
            self._run_async(prod.id),
            name="run-production",
            exclusive=True,
        )

    @property
    def stream(self) -> AgentStream:
        return self.query_one(AgentStream)

    @property
    def side_panel(self) -> SidePanel:
        return self.query_one(SidePanel)

    async def _run_async(self, production_id: str) -> None:
        self._run_error = None
        try:
            await self.api.run_production(production_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - erreurs LLM/fournisseur : pas de crash TUI
            message = str(exc) or f"{type(exc).__name__}"
            self._run_error = message
            self.api.fail_production(production_id, message)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "run-production":
            return
        if event.state not in (WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED):
            return
        worker = event.worker
        status_bar = self.query_one(StatusBar)
        status_bar.set_running(False)
        self.task_bar.set_running(False)

        if event.state is WorkerState.CANCELLED:
            self.stream.write_line("Run cancelled", theme.WARNING)
            status_bar.set_step("cancelled")
            return
        if event.state is WorkerState.ERROR:
            error = worker.error
            message = str(error) if error else "Run failed"
            self.stream.write_line(f"Run failed: {_first_error_line(message)}", theme.ERROR)
            status_bar.set_step("failed")
            self.notify(f"Run failed: {_first_error_line(message)}", severity="error")
            return

        if self._run_error:
            first = _first_error_line(self._run_error)
            self.stream.write_line(f"Run failed: {first}", theme.ERROR)
            status_bar.set_step("failed")
            self.notify(f"Run failed: {first}", severity="error")
            prod = self.api.get_production(self._current.id) if self._current else None
            self.side_panel.update_production(prod)
            self._run_error = None
            return

        outcome = worker.result
        self.stream.write_line(f"Pipeline finished - {self._outcome_summary(outcome)}", theme.SUCCESS)
        status_bar.set_step("completed")
        self.side_panel.update_production(self.api.get_production(self._current.id) if self._current else None)

    def _outcome_summary(self, outcome: object) -> str:
        run = getattr(outcome, "run", None)
        if run is not None and getattr(run, "status", None):
            revisions = getattr(outcome, "revisions", None)
            summary = str(run.status)
            if revisions:
                summary += f" ({revisions} revision(s))"
            return summary
        for attr in ("status", "message", "reason"):
            value = getattr(outcome, attr, None)
            if value:
                return str(value)
        return repr(outcome) if outcome is not None else ""

    @on(Button.Pressed, "#btn-cancel")
    def _on_cancel(self) -> None:
        if self._run_worker is not None:
            self._run_worker.cancel()
        self.api.cancel_production()

    @on(Button.Pressed, "#btn-copy")
    def _on_copy(self) -> None:
        self.action_copy_stream()

    def action_copy_stream(self) -> None:
        """Copia le flux d'agents courant vers le presse-papiers."""
        text = self.stream.export_text()
        if not text.strip():
            self.notify("Nothing to copy yet", severity="warning")
            return
        self.app.copy_to_clipboard(text)
        self.notify("Stream copied to clipboard", severity="information")

    # ========== live stream handling ==========

    def action_event_detail(self) -> None:
        """Open the event detail overlay (full content of the latest events)."""
        if not self._event_ring:
            self.notify("No events to inspect yet", severity="warning")
            return
        from DeepBl4nder.tui.screens.event_detail import EventDetailScreen

        self.app.push_screen(EventDetailScreen(self._event_ring, index=len(self._event_ring) - 1))

    def _handle_event(self, event: StreamEvent) -> None:
        self._event_ring.append(event)
        kind = event.kind
        status_bar = self.query_one(StatusBar)

        if kind == "run_started":
            status_bar.set_running(True)
        elif kind in ("run_completed", "run_blocked", "run_failed", "run_cancelled"):
            status_bar.set_running(False)
            self.task_bar.set_running(False)
        elif kind in ("step_started",):
            status_bar.set_step(event.content.replace("step started: ", ""))
        elif kind == "revision_requested":
            status_bar.set_step("revising")

        if kind in ("cost_recorded", "llm_complete", "call_end"):
            cost = self._extract_cost(event, kind)
            if cost:
                self._cost += cost
                status_bar.set_cost(self._cost)

        if kind == "budget_alert":
            self.notify("Budget exceeded - pipeline halted", severity="warning")

        # La rotation LLM est LIVE : dès qu'un fournisseur répond (ou échoue
        # et passe en cooldown), on rafraîchit l'étiquette fournisseur/modèle.
        # Pas seulement aux frontières d'étape, sinon "model:" reste figé sur
        # le premier fournisseur du pool.
        if kind in ("llm_call", "llm_complete", "call_end", "call_start"):
            self._refresh_provider_label()
        elif kind in ("step_started", "step_completed", "step_failed"):
            self._refresh_provider_label()

        self.stream.write_event(event)

        if kind in ("run_started", "step_completed", "step_failed", "cost_recorded", "run_completed", "run_failed", "revision_requested"):
            self._refresh_side_panel()

    _COST_KEYS = {"cost_recorded": "cost", "llm_complete": "cost_usd", "call_end": "cost"}

    def _extract_cost(self, event: StreamEvent, kind: str) -> float:
        return float((event.meta or {}).get(self._COST_KEYS.get(kind, ""), 0.0) or 0.0)

    def _refresh_side_panel(self) -> None:
        if not self._current:
            return
        prod = self.api.get_production(self._current.id)
        self.side_panel.update_production(prod)
        self.side_panel.update_budget(self.api.budget.report())
        self._refresh_provider_label()

    def _provider_info(self) -> tuple[str, list[str]]:
        stats = self.api.router_stats()
        providers = stats.get("providers") or []
        status = self.api.get_agent_status()
        # Vainqueur réel du dernier appel (rotation) ; chaine vide tant
        # qu'aucun fournisseur n'a répondu (pas un faux modèle statique).
        models = sorted(
            {
                info["model"]
                for info in status.values()
                if info.get("available") and info.get("model") not in (None, "", "unknown")
            }
        )
        last = self.api.last_llm_decision()
        if last.get("model") and last["model"] not in models:
            models = sorted([*models, last["model"]])
        if not models:
            # Aucune réponse réussie : on montre quand même la recherche —
            # la dernière tentative (fournisseur, modèle, erreur) plutôt
            # qu'un "no reply" figé.
            attempt = self.api.last_llm_attempt()
            if attempt.get("model") and attempt.get("provider"):
                hint = f" · {attempt.get('error', '')}" if attempt.get("error") else ""
                models = [f"[dim]{attempt['model']}{hint}[/dim]"]
        if not providers:
            label = ", ".join(models[:3]) if models else "no provider"
            return label, models
        parts = [f"mode {stats.get('rotation', '?')}"]
        for provider in providers[:4]:
            hints = []
            if provider.get("wins"):
                hints.append(f"{provider['wins']}w")
            if provider.get("failures"):
                hints.append(f"{provider['failures']}f")
            cooldown = provider.get("cooldown_remaining_s", 0)
            if cooldown > 0:
                hints.append(f"cool {cooldown:.0f}s")
            label = provider.get("id", "?")
            parts.append(f"{label} ({', '.join(hints)})" if hints else label)
        return " · ".join(parts), models

    def _refresh_provider_label(self) -> None:
        provider_line, models = self._provider_info()
        self.query_one(StatusBar).set_provider(provider_line)
        self.side_panel.update_llm(provider_line, models)

    def _stream_fail(self, message: str) -> None:
        self.stream.write_line(message, theme.ERROR)