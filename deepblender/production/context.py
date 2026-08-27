"""Injection de contexte NOOA dans les agents du pipeline.

Le module ``context.py`` centralise la logique d'injection de variables
de contexte (``run_history``, ``revision_feedback``, etc.) dans les
agents du pipeline, en isolant cette responsabilité du ``PipelineRunner``.

Utilisé en duck-typing : chaque agent peut exposer un attribut ``context``
(behaviour ``__setitem__``) ; les agents sans ``context`` sont ignorés.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deepblender.domain.qa import QAReport


class ContextInjector:
    """Injecte des variables de contexte dans les agents du pipeline.

    Le constructeur reçoit la liste des agents ``(nom, agent)`` telle que
    construite par le ``PipelineRunner``. Les agents dont l'attribut
    ``context`` est ``None`` (stubs de test, agents désactivés) sont
    silencieusement ignorés.
    """

    def __init__(
        self,
        agents: list[tuple[str, Any]],
        event_log: Any,
        workdir: Path,
    ) -> None:
        self._agents = agents
        self.event_log = event_log
        self.workdir = workdir

    def _agents_with_context(self) -> list[tuple[Any, Any]]:
        """Couples (agent, context) des agents du pipeline (duck-typed)."""
        pairs: list[tuple[Any, Any]] = []
        for _name, agent in self._agents:
            if agent is None:
                continue
            context = getattr(agent, "context", None)
            if context is not None:
                pairs.append((agent, context))
        return pairs

    def _set_context(self, context: Any, key: str, value: str) -> None:
        """Ecrit une variable de contexte NOOA (``set_static`` si disponible)."""
        set_static = getattr(context, "set_static", None)
        if callable(set_static):
            set_static(key, value)
        elif hasattr(context, "set"):
            context.set(key, value)
        else:
            context[key] = value

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

    def inject_run_history(self) -> None:
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

    def inject_revision_feedback(self, target: str, report: QAReport, revision: int, agents_map: dict[str, Any] | None = None) -> None:
        """Injecte le feedback QA dans le contexte NOOA de l'agent ciblé.

        L'agent (BlenderAgent / DirectorAgent) lit ensuite ``revision_feedback``
        via ``self.context`` pour corriger le tir lors de la régénération.
        Les agents stub (tests) sans ``context`` sont ignorés silencieusement.

        Parameters
        ----------
        target:
            Nom de l'étape cible (``"director"`` ou ``"blender"``).
        report:
            Rapport QA dont on formate le feedback.
        revision:
            Numéro de la révision courante.
        agents_map:
            Dictionnaire ``{nom_étape: agent}`` pour résoudre la cible.
            Si ``None``, on reconstruit à partir de ``self._agents``.
        """
        if agents_map is None:
            agent_dict: dict[str, Any] = {name: agent for name, agent in self._agents}
            agent = agent_dict.get(target)
        else:
            agent = agents_map.get(target)
        if agent is None:
            return
        context = getattr(agent, "context", None)
        if context is None:
            return
        feedback = self._format_feedback(report, revision)
        self._set_context(context, "revision_feedback", feedback)

    def latest_revision_request(self) -> dict[str, Any] | None:
        """Demande de révision humaine (HITL) la plus récente du workdir.

        ``request_revision`` (API) écrit ``revision_request_<ts>.json`` avant de
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

    def inject_human_feedback(self, target: str, comment: str, agents_map: dict[str, Any] | None = None) -> None:
        """Injection HITL : le commentaire humain devient ``revision_feedback``.

        Contrairement à la boucle QA (feedback issu d'un rapport), ici le
        feedback vient d'un humain via le formulaire de révision. Il est
        injecté dans l'agent ciblé (director ou blender, défaut blender) avant
        de rejouer le pipeline.

        Parameters
        ----------
        target:
            Nom de l'étape cible (``"director"`` ou ``"blender"``).
        comment:
            Commentaire humain à injecter.
        agents_map:
            Dictionnaire ``{nom_étape: agent}`` pour résoudre la cible.
            Si ``None``, on reconstruit à partir de ``self._agents``.
        """
        if not comment.strip():
            return
        if agents_map is None:
            agent_dict: dict[str, Any] = {name: agent for name, agent in self._agents}
            agent = agent_dict.get(target, None)
            # Fallback : si la cible n'est pas dans la map, prendre le premier agent non-None
            if agent is None:
                for _name, a in self._agents:
                    if a is not None:
                        agent = a
                        break
        else:
            agent = agents_map.get(target, None)
            if agent is None:
                agent = next(iter(agents_map.values()), None)
        if agent is None:
            return
        context = getattr(agent, "context", None)
        if context is None:
            return
        feedback = f"### Révision humaine\nInstructions du producteur :\n{comment}"
        self._set_context(context, "revision_feedback", feedback)

    def consume_revision_requests(self) -> None:
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