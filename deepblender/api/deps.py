"""Dépendances FastAPI : authentification et scope par tenant.

`get_current_user` valide le JWT ; `require_membership` vérifie l'appartenance
à une organisation (isolation multi-tenant) ; `require_role` applique le RBAC.
Les ressources hors du tenant renvoient 404 (pas de fuite d'existence).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from deepblender.api.db import DbSession
from deepblender.api.models import Membership, Organization, Production, Project, User, Workspace
from deepblender.api.security import decode_token_full
from deepblender.api.state import get_secret_key

_bearer = HTTPBearer(auto_error=False)

ROLE_READ = ("owner", "admin", "editor", "viewer")
ROLE_WRITE = ("owner", "admin", "editor")
ROLE_MANAGE = ("owner", "admin")


def get_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return credentials.credentials


def get_current_user(
    db: DbSession,
    token: Annotated[str, Depends(get_token)],
) -> User:
    payload = decode_token_full(token, get_secret_key())
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="invalid or expired token")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_membership(db: Session, organization_id: str, user: User) -> Membership:
    """Renvoie l'appartenance de `user` à l'org, ou 404 (isolation tenant)."""
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return membership


def require_role(membership: Membership, *roles: str) -> Membership:
    """Vérifie que le rôle de l'appartenance autorise l'action (RBAC)."""
    if membership.role not in roles:
        raise HTTPException(status_code=403, detail="insufficient permissions")
    return membership


def scoped_workspace(db: Session, user: User, workspace_id: str) -> tuple[Workspace, Membership]:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    membership = require_membership(db, workspace.organization_id, user)
    return workspace, membership


def scoped_project(db: Session, user: User, project_id: str) -> tuple[Project, Membership]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    membership = require_membership(db, project.organization_id, user)
    return project, membership


def scoped_production(db: Session, user: User, production_id: str) -> tuple[Production, Membership]:
    production = db.get(Production, production_id)
    if production is None:
        raise HTTPException(status_code=404, detail="production not found")
    membership = require_membership(db, production.organization_id, user)
    return production, membership


def get_organization(db: Session, organization_id: str) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return organization
