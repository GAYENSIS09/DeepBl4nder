"""Schémas Pydantic (validation + sérialisation) de l'API SaaS."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ROLES = ("owner", "admin", "editor", "viewer")
_STATUSES = (
    "draft",
    "queued",
    "running",
    "waiting_approval",
    "revising",
    "completed",
    "failed",
    "cancelled",
    "blocked",
)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value.lower()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value.lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    created_at: datetime


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: str
    role: str


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    owner_id: str
    created_at: datetime
    role: str = ""


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    full_name: str
    role: str


class OrgDetailOut(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime
    role: str
    members: list[MemberOut]


class MemberAdd(BaseModel):
    email: str
    role: str = "viewer"

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value.lower()

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: str) -> str:
        if value not in _ROLES:
            raise ValueError(f"role must be one of {_ROLES}")
        return value


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    organization_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime


class ProductionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    brief: str = Field(min_length=1, max_length=20000)


class ProductionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    organization_id: str
    name: str
    brief: str
    status: str
    current_step: str
    progress: float
    cost: float
    version: int
    error: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ArtifactOut(BaseModel):
    """Méta-information d'un artifact produit par un run."""

    name: str
    type: str
    path: str
    size: int
    cost: float = 0.0


class RevisionRequest(BaseModel):
    """Demande de révision manuelle d'une production (human-in-the-loop)."""

    target_step: str = Field(default="director", max_length=64)
    comment: str = Field(default="", max_length=2000)


class WorkerRunOut(BaseModel):
    """Run en cours d'exécution sur le worker."""

    production_id: str
    since: float


class RoutingProviderOut(BaseModel):
    """Santé d'un fournisseur LLM vu par le routeur multi-fournisseurs."""

    id: str
    model: str
    base_url: str
    successes: int
    failures: int
    cooldown_until: float
    cooldown_remaining_s: float
    last_error: str | None = None


class WorkerOut(BaseModel):
    """État du worker (file d'exécution intégrée à l'API)."""

    status: str
    queue_depth: int
    running: list[WorkerRunOut]
    processed: int
    failed: int
    last_heartbeat: float
    rotation: str = "adaptive"
    routing: list[RoutingProviderOut] = []


class UsageQuotas(BaseModel):
    """Quotas d'usage configurés (None = illimité)."""

    productions: int | None = None
    cost: float | None = None


class UsageOut(BaseModel):
    """Consommation et quotas de l'utilisateur courant."""

    productions: int
    runs: int
    total_cost: float
    quotas: UsageQuotas


class SequenceOut(BaseModel):
    id: str
    name: str
    order_index: int
    scenes: list["SceneOut"] = []


class SceneOut(BaseModel):
    id: str
    name: str
    order_index: int
    status: str
    shots: list["ShotOut"] = []


class ShotOut(BaseModel):
    id: str
    index: int
    start: float
    end: float
    camera_summary: str
    action: str
    status: str


class TimelineOut(BaseModel):
    production_id: str
    sequences: list[SequenceOut]


class PatchRequest(BaseModel):
    """Patch structuré pour modifier un paramètre précis d'un shot/scène."""
    target: str  # ex: "shots[0].camera.position"
    old_value: Any | None = None
    new_value: Any
    rationale: str = ""


class PatchResponse(BaseModel):
    patch_id: str
    status: str
    message: str


class ArtifactRecordOut(BaseModel):
    id: str
    type: str
    name: str
    version: int
    path: str
    sha256: str
    status: str
    cost: float
    parent_ids: list[str] = []
    created_at: datetime


class ArtifactRecordsOut(BaseModel):
    records: list[ArtifactRecordOut]


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=2048)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=2048)
