"""Artifact registry : versioning, hash, statuts ; provenance et dépendances."""

from __future__ import annotations

from DeepBl4nder.artifacts.provenance import ProvenanceGraph
from DeepBl4nder.artifacts.registry import Artifact, ArtifactRegistry


def _make(tmp_path, name: str, content: str) -> Artifact:  # noqa: ANN001
    path = tmp_path / f"{name}.png"
    path.write_text(content, encoding="utf-8")
    return Artifact(type="render", name=name, path=path)


def test_register_versions_by_type_and_name(tmp_path) -> None:  # noqa: ANN001
    registry = ArtifactRegistry()
    first = registry.register(_make(tmp_path, "shot-01", "v1"))
    second = registry.register(_make(tmp_path, "shot-01", "v2"))
    assert first.version == 1
    assert second.version == 2
    assert registry.latest("render", "shot-01") == second
    assert len(registry.versions("render", "shot-01")) == 2


def test_register_computes_hash(tmp_path) -> None:  # noqa: ANN001
    registry = ArtifactRegistry()
    artifact = registry.register(_make(tmp_path, "a", "contenu"))
    assert artifact.sha256
    assert len(artifact.sha256) == 64


def test_status_lifecycle(tmp_path) -> None:  # noqa: ANN001
    registry = ArtifactRegistry()
    artifact = registry.register(_make(tmp_path, "b", "x"))
    registry.set_status(artifact.id, "approved")
    assert registry.get(artifact.id) is not None
    assert registry.get(artifact.id).status == "approved"  # type: ignore[union-attr]


def test_provenance_chain() -> None:
    graph = ProvenanceGraph()
    graph.record("brief", "scene-spec")
    graph.record("scene-spec", "script")
    graph.record("script", "render")
    assert graph.chain("render") == ["brief", "scene-spec", "script", "render"]
    assert graph.parents("script") == ["scene-spec"]
    assert graph.dependents("script") == ["render"]


def test_provenance_branches() -> None:
    graph = ProvenanceGraph()
    graph.record("brief", "story")
    graph.record("brief", "storyboard")
    graph.record("story", "script")
    graph.record("script", "render")
    assert graph.chain("render") == ["brief", "story", "script", "render"]
    assert set(graph.children("brief")) == {"story", "storyboard"}
