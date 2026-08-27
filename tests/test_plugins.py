"""Plugins (frontières externes) et tools (primitives d'action)."""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import cast

from DeepBl4nder.codegen import CodePolicyViolation
from DeepBl4nder.bridges.blender.bridge import BlenderNotFoundError
from DeepBl4nder.domain.scene import BlenderScript
from DeepBl4nder.plugins.knowledge.asset_library import AssetLibraryPlugin
from DeepBl4nder.plugins.media.audio import AudioPlugin
from DeepBl4nder.plugins.rendering.blender import BlenderPlugin
from DeepBl4nder.plugins.registry import PluginRegistry
from DeepBl4nder.plugins.storage.storage import StoragePlugin
from DeepBl4nder.plugins.media.subtitle import SubtitleEntry, SubtitlePlugin
from DeepBl4nder.plugins.tools import ToolRegistry


def test_plugin_registry_registers_builtins() -> None:
    registry = PluginRegistry()
    # Lazy: utiliser get_or_create pour instancier chaque plugin
    for name in ["blender", "ffmpeg", "audio", "tts", "storage", "asset-library", "subtitle", "git", "knowledge-graph", "render-farm"]:
        registry.get_or_create(name)
    names = {plugin.name for plugin in registry.all_plugins()}
    assert names == {
        "blender",
        "ffmpeg",
        "audio",
        "tts",
        "storage",
        "asset-library",
        "subtitle",
        "git",
        "knowledge-graph",
        "render-farm",
    }


def test_plugin_registry_unknown_plugin() -> None:
    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.get("does-not-exist")
    # get_or_create aussi lève pour builtins inconnus
    with pytest.raises(KeyError):
        registry.get_or_create("does-not-exist")


def test_blender_plugin_available_false_without_binary() -> None:
    plugin = BlenderPlugin()
    plugin.bridge._blender_exe = "definitely-not-blender"
    assert not plugin.available()


def test_execute_python_rejects_policy_violation(tmp_path: Path) -> None:
    plugin = BlenderPlugin()
    plugin.bridge._blender_exe = "definitely-not-blender"
    evil = BlenderScript(code="import os\nos.system('rm -rf /')\n", scene_name="evil")
    with pytest.raises(CodePolicyViolation):
        plugin.execute_python(evil)


def test_plugin_templates_pass_policy(tmp_path: Path) -> None:
    """Les templates inspect/render/save/load sont conformes à la politique."""
    plugin = BlenderPlugin()
    plugin.bridge._blender_exe = "definitely-not-blender"
    with pytest.raises(BlenderNotFoundError):
        plugin.inspect_scene()
    with pytest.raises(BlenderNotFoundError):
        plugin.render()
    with pytest.raises(BlenderNotFoundError):
        plugin.save_scene("scene", tmp_path / "scene.blend")
    with pytest.raises(BlenderNotFoundError):
        plugin.load_asset("scene", tmp_path / "prop.blend")


def test_inspect_render_checks_artifact(tmp_path: Path) -> None:
    plugin = BlenderPlugin()
    assert plugin.inspect_render(tmp_path / "missing.png")["exists"] is False
    render = tmp_path / "render.png"
    render.write_bytes(b"png-bytes")
    report = plugin.inspect_render(render)
    assert report["exists"] is True
    assert report["ok"] is True
    assert report["bytes"] == len(b"png-bytes")


def test_audio_plugin_generates_deterministic_ambience(tmp_path: Path) -> None:
    plugin = AudioPlugin()
    first = plugin.generate_ambience(0.1, tmp_path / "a.wav", seed=3)
    second = plugin.generate_ambience(0.1, tmp_path / "b.wav", seed=3)
    assert first.read_bytes() == second.read_bytes()
    info = plugin.inspect(first)
    assert info["duration"] == pytest.approx(0.1, abs=0.01)


def test_storage_plugin_roundtrip(tmp_path: Path) -> None:
    plugin = StoragePlugin(root=tmp_path / "store")
    artifact = tmp_path / "render.png"
    artifact.write_bytes(b"data")
    key = plugin.store(artifact, "scenes/s1/render.png")
    assert key == tmp_path / "store" / "scenes" / "s1" / "render.png"
    assert plugin.retrieve("scenes/s1/render.png").read_bytes() == b"data"
    assert plugin.keys("scenes") == ["scenes/s1/render.png"]


def test_subtitle_plugin_roundtrip(tmp_path: Path) -> None:
    plugin = SubtitlePlugin()
    path = tmp_path / "subs.srt"
    plugin.generate([SubtitleEntry(index=1, start=0.0, end=2.0, text="Salut")], path)
    entries = plugin.parse(path)
    assert len(entries) == 1
    assert entries[0].text == "Salut"
    assert entries[0].start == 0.0
    assert entries[0].end == 2.0


def test_asset_library_register_and_find(tmp_path: Path) -> None:
    plugin = AssetLibraryPlugin(index_path=tmp_path / "index.json")
    asset = tmp_path / "hero.blend"
    asset.write_bytes(b"blend")
    entry = plugin.register(asset, "character", tags=["hero"])
    assert entry["type"] == "character"
    assert len(plugin.find("hero")) == 1
    assert plugin.find() == [entry]


def test_tool_registry_lists_canonical_tools() -> None:
    assert ToolRegistry().names() == [
        "inspect_scene",
        "load_asset",
        "save_blend",
        "render",
        "inspect_render",
        "create_audio",
        "compose",
        "export",
    ]


def test_tool_get_unknown_raises() -> None:
    with pytest.raises(KeyError):
        ToolRegistry().get("move_object")


def test_tool_render_routes_to_plugin() -> None:
    registry = ToolRegistry()
    blender = cast(BlenderPlugin, registry.plugins.get_or_create("blender"))
    blender.bridge._blender_exe = "definitely-not-blender"
    with pytest.raises(BlenderNotFoundError):
        registry.get("render").execute()


def test_tool_create_audio_produces_file(tmp_path: Path) -> None:
    registry = ToolRegistry()
    out = tmp_path / "ambience.wav"
    registry.get("create_audio").execute(0.2, out, seed=1)
    assert out.is_file()
    assert out.stat().st_size > 0


def test_knowledge_graph_add_node_and_query(tmp_path: Path) -> None:
    from DeepBl4nder.plugins.knowledge.knowledge_graph import KnowledgeGraphPlugin

    kg = KnowledgeGraphPlugin(path=tmp_path / "kg.json")
    kg.add_node("nina", "Character", {"language": "fr"})
    kg.add_node("ruelle", "Scene", {"mood": "dark"})
    kg.add_edge("nina", "ruelle", "appears_in")

    results = kg.query("nina", depth=1)
    assert len(results) >= 1
    assert any(r["source"] == "nina" and r["target"] == "ruelle" for r in results)
