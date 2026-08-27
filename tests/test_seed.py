"""Tests du seed de développement (compte admin idempotent)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from DeepBl4nder.api.db import Base, create_engine_for
from DeepBl4nder.api.models import Membership, Organization, Project, User, Workspace
from DeepBl4nder.api.seed import MIN_PASSWORD_LENGTH, seed_admin


@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine_for(f"sqlite:///{tmp_path / 'seed.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


def test_seed_creates_admin_org_and_project(db: Session) -> None:
    result = seed_admin(
        db,
        email="admin@DeepBl4nder.local",
        password="admin-dev-123",
        org_name="DeepBl4nder Dev",
        project_name="Démo",
    )
    db.commit()

    assert result.user_created and result.org_created
    user = db.query(User).filter(User.email == "admin@DeepBl4nder.local").one()
    assert user.is_active
    membership = db.query(Membership).filter(Membership.user_id == user.id).one()
    assert membership.role == "admin"
    organization = db.query(Organization).filter(Organization.id == membership.organization_id).one()
    assert organization.name == "DeepBl4nder Dev"
    workspace = db.query(Workspace).filter(Workspace.organization_id == organization.id).one()
    assert workspace.name == "Default"
    project = db.query(Project).filter(Project.organization_id == organization.id).one()
    assert project.name == "Démo"
    assert project.created_by == user.id


def test_seed_is_idempotent(db: Session) -> None:
    seed_admin(db, email="a@b.c", password="password-123")
    db.commit()
    first = db.query(User).filter(User.email == "a@b.c").count()

    result = seed_admin(db, email="a@b.c", password="password-123")
    db.commit()

    assert db.query(User).filter(User.email == "a@b.c").count() == first
    assert not result.user_created and not result.org_created
    assert not result.workspace_created and not result.project_created


def test_seed_resets_password(db: Session) -> None:
    from DeepBl4nder.api.security import verify_password

    seed_admin(db, email="a@b.c", password="password-123")
    db.commit()

    result = seed_admin(db, email="a@b.c", password="autre-mot-de-passe")
    db.commit()

    user = db.query(User).filter(User.email == "a@b.c").one()
    assert verify_password("autre-mot-de-passe", user.password_hash)
    assert not result.user_created


def test_seed_rejects_short_password(db: Session) -> None:
    short = "x" * (MIN_PASSWORD_LENGTH - 1)
    with pytest.raises(ValueError, match="trop court"):
        seed_admin(db, email="a@b.c", password=short)
