"""Domaine métier de DeepBl4nder : objets vivants typés manipulés par les agents NOOA."""

from __future__ import annotations

from DeepBl4nder.domain.asset import Asset, AssetKind, sha256_of_file
from DeepBl4nder.domain.media import (
    AudioMaster,
    AudioPlan,
    CompositeSpec,
    LanguagePackage,
    MusicCue,
    MusicPlan,
    SoundDesignPlan,
    SoundLayer,
)
from DeepBl4nder.domain.project import Brief, Project, Sequence, Shot
from DeepBl4nder.domain.qa import Issue, IssueKind, QAReport, QAStatus, RevisionSpec
from DeepBl4nder.domain.scene import (
    BlenderScript,
    CharacterSpec,
    EnvironmentSpec,
    RenderOutput,
    SceneSpec,
    ShotSpec,
)

__all__ = [
    "Asset",
    "AssetKind",
    "AudioMaster",
    "AudioPlan",
    "BlenderScript",
    "Brief",
    "CharacterSpec",
    "CompositeSpec",
    "EnvironmentSpec",
    "Issue",
    "IssueKind",
    "LanguagePackage",
    "MusicCue",
    "MusicPlan",
    "Project",
    "QAReport",
    "QAStatus",
    "RenderOutput",
    "RevisionSpec",
    "SceneSpec",
    "Sequence",
    "Shot",
    "ShotSpec",
    "SoundDesignPlan",
    "SoundLayer",
    "sha256_of_file",
]
