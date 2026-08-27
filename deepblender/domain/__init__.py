"""Domaine métier de DeepBlender : objets vivants typés manipulés par les agents NOOA."""

from __future__ import annotations

from deepblender.domain.asset import Asset, AssetKind, sha256_of_file
from deepblender.domain.media import (
    AudioMaster,
    AudioPlan,
    CompositeSpec,
    LanguagePackage,
    MusicCue,
    MusicPlan,
    SoundDesignPlan,
    SoundLayer,
)
from deepblender.domain.project import Brief, Project, Sequence, Shot
from deepblender.domain.qa import Issue, IssueKind, QAReport, QAStatus, RevisionSpec
from deepblender.domain.scene import (
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
