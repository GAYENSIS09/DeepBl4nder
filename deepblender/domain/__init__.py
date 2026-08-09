"""Domaine métier de DeepBlender : objets vivants typés manipulés par les agents NOOA."""

from __future__ import annotations

from deepblender.domain.asset import Asset, AssetKind, sha256_of_file
from deepblender.domain.media import AudioMaster, AudioPlan, CompositeSpec, LanguagePackage
from deepblender.domain.project import Brief, Project, Sequence, Shot
from deepblender.domain.qa import Issue, IssueKind, QAReport, QAStatus, RevisionSpec
from deepblender.domain.scene import (
    AnimationSpec,
    BlenderScript,
    CameraSpec,
    CharacterSpec,
    EnvironmentSpec,
    LightingSpec,
    SceneSpec,
    ShotSpec,
)

__all__ = [
    "AnimationSpec",
    "Asset",
    "AssetKind",
    "AudioMaster",
    "AudioPlan",
    "BlenderScript",
    "Brief",
    "CameraSpec",
    "CharacterSpec",
    "CompositeSpec",
    "EnvironmentSpec",
    "Issue",
    "IssueKind",
    "LanguagePackage",
    "LightingSpec",
    "Project",
    "QAReport",
    "QAStatus",
    "RevisionSpec",
    "SceneSpec",
    "Sequence",
    "Shot",
    "ShotSpec",
    "sha256_of_file",
]
