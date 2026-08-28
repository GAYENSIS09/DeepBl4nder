"""Registry de skills : découverte, chargement NOOA, progressive disclosure."""

from __future__ import annotations

from DeepBl4nder.skills.registry import SkillRegistry


def test_default_registry_discovers_packaged_skills() -> None:
    registry = SkillRegistry()
    names = {info.name for info in registry.discover()}
    assert {"blender-python", "cinematography", "lighting", "animation", "qa", "storyboard"} <= names
    for info in registry.discover():
        assert info.description


def test_resolve_loads_textskill() -> None:
    registry = SkillRegistry()
    skill = registry.resolve("blender-python")
    assert "Blender" in (skill.__doc__ or "")


def test_resolve_unknown_raises() -> None:
    registry = SkillRegistry()
    try:
        registry.resolve("does-not-exist")
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_summaries() -> None:
    registry = SkillRegistry()
    summaries = registry.summaries()
    assert any("blender-python" in s for s in summaries)


def test_custom_root(tmp_path) -> None:
    skill_dir = tmp_path / "custom-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: custom-skill\ndescription: Un skill de test.\n---\n\n# Contenu",
        encoding="utf-8",
    )
    registry = SkillRegistry(root=tmp_path)
    assert registry.resolve("custom-skill") is not None
    infos = registry.discover()
    assert len(infos) == 1
    assert infos[0].description == "Un skill de test."
