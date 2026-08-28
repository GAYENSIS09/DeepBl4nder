"""Objet domaine : specs, QA, hashing."""

from __future__ import annotations

from DeepBl4nder.domain.asset import sha256_of_file
from DeepBl4nder.domain.qa import Issue, IssueKind, QAReport, QAStatus, RevisionSpec
from DeepBl4nder.domain.scene import CharacterSpec, SceneSpec, ShotSpec


def test_shot_spec_frame_count() -> None:
    shot = ShotSpec(duration=5.0, fps=24)
    assert shot.frame_count() == 120


def test_shot_spec_defaults() -> None:
    shot = ShotSpec()
    assert shot.fps == 24
    assert shot.camera.focal_length_mm == 50.0
    assert shot.environment.rain is False


def test_scene_spec_mapping() -> None:
    spec = SceneSpec(brief="ruelle sous la pluie", shots=[ShotSpec(), ShotSpec()])
    mapping = spec.to_mapping()
    assert mapping["brief"] == "ruelle sous la pluie"
    assert mapping["shots"] == 2


def test_character_spec_multilingual() -> None:
    char = CharacterSpec(name="Awa", main_language="fr", languages=["en", "wo"])
    assert char.spoken_languages() == ["fr", "en", "wo"]

    bilingual = CharacterSpec(name="Ibou", languages=["fr"])
    assert bilingual.spoken_languages() == ["fr"]

    mapping = char.to_mapping()
    assert mapping["main_language"] == "fr"
    assert mapping["languages"] == ["en", "wo"]


def test_qa_report_status() -> None:
    ok = QAReport(passed=True, score=0.9)
    ko = QAReport(passed=False, score=0.3, issues=[Issue(kind=IssueKind.VISUAL, message="trop sombre")])
    assert ok.status is QAStatus.PASS
    assert ko.status is QAStatus.FAIL


def test_revision_targets_a_step() -> None:
    revision = RevisionSpec(issues=[Issue(kind=IssueKind.CONTINUITY, message="costume incohérent")], target_step="lookdev")
    assert revision.target_step == "lookdev"


def test_sha256_of_file(tmp_path) -> None:
    f = tmp_path / "asset.bin"
    f.write_bytes(b"DeepBl4nder")
    assert sha256_of_file(f) == sha256_of_file(f)
    assert len(sha256_of_file(f)) == 64
