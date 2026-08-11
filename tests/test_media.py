"""Domaine média : audio, compositing et localisation."""

from __future__ import annotations

from deepblender.domain.media import AudioMaster, AudioPlan, CompositeSpec, LanguagePackage


def test_audio_plan_mapping() -> None:
    plan = AudioPlan(mood="suspense", music_theme="pulsing", tempo=90.0, sfx_events=["rain", "door"])
    mapping = plan.to_mapping()
    assert mapping["mood"] == "suspense"
    assert mapping["sfx"] == 2


def test_audio_master_fields() -> None:
    master = AudioMaster(path="mix.wav", duration=12.0, channels=2)
    assert master.sample_rate == 44100
    assert master.duration == 12.0


def test_composite_spec_defaults() -> None:
    spec = CompositeSpec()
    assert "diffuse" in spec.passes
    assert spec.output_format == "exr"


def test_composite_spec_mapping() -> None:
    spec = CompositeSpec(passes=["diffuse", "mist"], grade="filmic", effects=["bloom"])
    mapping = spec.to_mapping()
    assert mapping["passes"] == 2
    assert mapping["grade"] == "filmic"
    assert mapping["effects"] == ["bloom"]
    assert mapping["output_format"] == "exr"


def test_language_package_includes_interface() -> None:
    package = LanguagePackage(
        language="fr",
        languages=["fr", "en", "wo"],
        subtitles_path="sub/fr.srt",
        interface={"play": "Lecture", "render": "Rendu"},
    )
    mapping = package.to_mapping()
    assert mapping["language"] == "fr"
    assert mapping["languages"] == 3
    assert mapping["interface_keys"] == 2
    assert mapping["subtitles_path"] == "sub/fr.srt"
