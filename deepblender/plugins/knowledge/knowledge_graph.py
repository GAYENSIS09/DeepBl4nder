"""KnowledgeGraphPlugin : graphe de connaissances de la production (JSON)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepblender.plugins.base import Plugin, PluginError


@dataclass
class KnowledgeGraphPlugin(Plugin):
    """Relie les entités de la production (scènes, plans, assets, décisions)."""

    name: str = "knowledge-graph"
    description: str = "Graphe de connaissances de la production (JSON)."
    path: Path = field(default_factory=lambda: Path.cwd() / "production" / "kg.json")

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"nodes": {}, "edges": []})

    def available(self) -> bool:
        return True

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {"nodes": {}, "edges": []}

    def _write(self, graph: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_node(self, node_id: str, label: str, props: dict[str, Any] | None = None) -> None:
        graph = self._read()
        graph["nodes"][node_id] = {"label": label, "props": props or {}, "updated_at": time.time()}
        self._write(graph)

    def add_edge(self, source: str, target: str, relation: str) -> None:
        graph = self._read()
        if source not in graph["nodes"] or target not in graph["nodes"]:
            raise PluginError(f"unknown node: {source if source not in graph['nodes'] else target}")
        graph["edges"].append({"source": source, "target": target, "relation": relation})
        self._write(graph)

    def query(self, center: str, depth: int = 1) -> list[dict[str, str]]:
        graph = self._read()
        if center not in graph["nodes"]:
            raise PluginError(f"node not found: {center}")
        result: list[dict[str, str]] = []
        frontier = {center}
        for _ in range(depth):
            neighbors: set[str] = set()
            for edge in graph["edges"]:
                if edge["source"] in frontier:
                    result.append({"source": edge["source"], "relation": edge["relation"], "target": edge["target"]})
                    neighbors.add(edge["target"])
                elif edge["target"] in frontier:
                    result.append({"source": edge["source"], "relation": edge["relation"], "target": edge["target"]})
                    neighbors.add(edge["source"])
            frontier = neighbors
        return result
