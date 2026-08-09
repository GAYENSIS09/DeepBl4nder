"""Provenance de production : graphe orienté répondant à « pourquoi cet artifact existe ? ».

La provenance permet reproductibilité, comparaison de versions, rollback,
audit, analyse des coûts et diagnostic (Roadmap A §20, C §22).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ProvenanceGraph:
    """Graphe parent -> enfant entre artifacts."""

    edges: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _parents: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def record(self, parent: str, child: str) -> None:
        """Relie un artifact parent à l'enfant qu'il a produit."""
        self.edges[parent].add(child)
        self._parents[child].add(parent)

    def parents(self, artifact_id: str) -> list[str]:
        """Parents directs d'un artifact (ce qui l'a produit)."""
        return sorted(self._parents.get(artifact_id, set()))

    def children(self, artifact_id: str) -> list[str]:
        """Enfants directs d'un artifact (ce qu'il a produit)."""
        return sorted(self.edges.get(artifact_id, set()))

    def chain(self, artifact_id: str) -> list[str]:
        """Chaîne de provenance de la source jusqu'à l'artifact (racine d'abord)."""
        ancestors: list[str] = []
        seen: set[str] = set()
        frontier = [artifact_id]
        while frontier:
            current = frontier.pop(0)
            for parent in self.parents(current):
                if parent in seen:
                    continue
                seen.add(parent)
                ancestors.append(parent)
                frontier.append(parent)
        ancestors.reverse()
        ancestors.append(artifact_id)
        return ancestors

    def dependents(self, artifact_id: str) -> list[str]:
        """Tous les artifacts à recalculer si cet artifact change (graphe de dépendance)."""
        result: list[str] = []
        seen: set[str] = set()
        frontier = [artifact_id]
        while frontier:
            current = frontier.pop(0)
            for child in self.children(current):
                if child in seen:
                    continue
                seen.add(child)
                result.append(child)
                frontier.append(child)
        return result
