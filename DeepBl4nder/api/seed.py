"""Seed de développement : crée un compte administrateur + org/workspace/projet.

Usage :

    python -m DeepBl4nder.api.seed [--db URL|fichier] [--email …] [--password …]

Idempotent : si le compte existe déjà, il est réactivé et son mot de passe
rejoué ; l'organisation et le projet ne sont créés que s'ils manquent.

Les identifiants se lisent aussi via l'environnement :

    DeepBl4nder_SEED_EMAIL     (défaut : admin@DeepBl4nder.local)
    DeepBl4nder_SEED_PASSWORD  (sinon mot de passe aléatoire affiché en sortie)
    DeepBl4nder_SEED_ORG       (défaut : DeepBl4nder Dev)
    DeepBl4nder_SEED_PROJECT   (défaut : Démo)

Jamais de mot de passe en dur dans le code ni le guide : il est fourni par
l'utilisateur ou généré et affiché une seule fois.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from dataclasses import dataclass

from sqlalchemy.orm import Session

from DeepBl4nder.api.db import Base, create_engine_for
from DeepBl4nder.api.models import Membership, Organization, Project, User, Workspace
from DeepBl4nder.api.security import hash_password

DEFAULT_EMAIL = "admin@DeepBl4nder.local"
DEFAULT_ORG = "DeepBl4nder Dev"
DEFAULT_PROJECT = "Démo"
MIN_PASSWORD_LENGTH = 8


@dataclass
class SeedResult:
    email: str
    password: str
    user_created: bool
    org_created: bool
    workspace_created: bool
    project_created: bool


def seed_admin(
    db: Session,
    *,
    email: str,
    password: str,
    org_name: str = DEFAULT_ORG,
    project_name: str = DEFAULT_PROJECT,
) -> SeedResult:
    """Crée ou met à jour le compte admin de dev et son org/projet de démo."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"mot de passe trop court ({len(password)} < {MIN_PASSWORD_LENGTH} caractères)"
        )

    user = db.query(User).filter(User.email == email).first()
    user_created = user is None
    if user is None:
        user = User(email=email, password_hash=hash_password(password), full_name="Admin DeepBl4nder")
        db.add(user)
        db.flush()
    else:
        user.password_hash = hash_password(password)
        user.full_name = user.full_name or "Admin DeepBl4nder"
        user.is_active = True

    organization = db.query(Organization).filter(Organization.name == org_name).first()
    org_created = organization is None
    if organization is None:
        organization = Organization(name=org_name, owner_id=user.id)
        db.add(organization)
        db.flush()

    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.organization_id == organization.id)
        .first()
    )
    if membership is None:
        db.add(Membership(user_id=user.id, organization_id=organization.id, role="admin"))

    workspace = (
        db.query(Workspace)
        .filter(Workspace.organization_id == organization.id, Workspace.name == "Default")
        .first()
    )
    workspace_created = workspace is None
    if workspace is None:
        workspace = Workspace(organization_id=organization.id, name="Default")
        db.add(workspace)
        db.flush()

    project = (
        db.query(Project)
        .filter(Project.organization_id == organization.id, Project.name == project_name)
        .first()
    )
    project_created = project is None
    if project is None:
        db.add(
            Project(
                workspace_id=workspace.id,
                organization_id=organization.id,
                name=project_name,
                description="Projet de démonstration créé par le seed de dev.",
                created_by=user.id,
            )
        )

    return SeedResult(
        email=email,
        password=password,
        user_created=user_created,
        org_created=org_created,
        workspace_created=workspace_created,
        project_created=project_created,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="DeepBl4nder.api.seed", description="Seed de développement DeepBl4nder.")
    parser.add_argument("--db", default=os.environ.get("DeepBl4nder_DB", "DeepBl4nder.db"), help="Base SQLAlchemy (URL ou fichier SQLite).")
    parser.add_argument("--email", default=os.environ.get("DeepBl4nder_SEED_EMAIL", DEFAULT_EMAIL))
    parser.add_argument("--password", default=os.environ.get("DeepBl4nder_SEED_PASSWORD", ""))
    parser.add_argument("--org", default=os.environ.get("DeepBl4nder_SEED_ORG", DEFAULT_ORG))
    parser.add_argument("--project", default=os.environ.get("DeepBl4nder_SEED_PROJECT", DEFAULT_PROJECT))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    password = args.password or secrets.token_urlsafe(12)
    generated = not args.password and not os.environ.get("DeepBl4nder_SEED_PASSWORD")

    engine = create_engine_for(args.db)
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        result = seed_admin(
            session,
            email=args.email,
            password=password,
            org_name=args.org,
            project_name=args.project,
        )
        session.commit()
    except ValueError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 2
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Compte admin : {result.email}  (rôle : admin sur « {args.org} »)")
    if generated:
        print(f"Mot de passe : {password}  ← généré, à noter (jamais stocké en clair)")
    print(f"Créé : user={result.user_created}, org={result.org_created}, "
          f"workspace={result.workspace_created}, projet={result.project_created}")
    print("Connexion : http://localhost:3000/login")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
