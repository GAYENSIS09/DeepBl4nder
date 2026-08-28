"""Application FastAPI : socle SaaS multi-tenant DeepBl4nder.

Endpoints : auth (register/login/me), organisations (membres + RBAC),
workspaces, projets et productions. L'isolation par tenant est garantie par
`require_membership` (les ressources d'un autre tenant renvoient 404).

La persistance (SQLite) et la clé secrète JWT sont configurables via
`create_app(database_url=..., secret_key=...)` ou les variables
d'environnement `DeepBl4nder_DB` / `DeepBl4nder_SECRET_KEY`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from DeepBl4nder import __version__
from DeepBl4nder.api.bus import AsyncEventBus
from DeepBl4nder.api.db import Base, DbSession, create_engine_for, create_session_factory
from DeepBl4nder.codegen.validator import ASTValidator, ValidationReport
from DeepBl4nder.api.deps import (
    ROLE_MANAGE,
    ROLE_READ,
    ROLE_WRITE,
    CurrentUser,
    get_organization,
    require_membership,
    require_role,
    scoped_production,
    scoped_project,
    scoped_workspace,
)
from DeepBl4nder.api.models import Membership, Organization, Production, Project, User, Workspace, Sequence, Scene, Patch, ArtifactRecord, RefreshToken
from DeepBl4nder.api.pipeline import run_production
from DeepBl4nder.api.schemas import (
    ArtifactOut,
    ArtifactRecordOut,
    ArtifactRecordsOut,
    LoginRequest,
    LogoutRequest,
    MeOut,
    MemberAdd,
    MemberOut,
    MembershipOut,
    OrgCreate,
    OrgDetailOut,
    OrgOut,
    ProductionCreate,
    ProductionOut,
    ProjectCreate,
    ProjectOut,
    RefreshTokenRequest,
    RegisterRequest,
    RevisionRequest,
    RoutingProviderOut,
    TokenResponse,
    UsageOut,
    UsageQuotas,
    UserOut,
    WorkerOut,
    WorkerRunOut,
    WorkspaceCreate,
    WorkspaceOut,
    TimelineOut,
    PatchRequest,
    PatchResponse,
    SequenceOut,
    SceneOut,
    ShotOut,
)
from DeepBl4nder.api.security import create_token, create_refresh_token, hash_password, hash_token, verify_password
from DeepBl4nder.api.state import WorkerStatus, configure, get_secret_key, get_session_factory
from DeepBl4nder.llm import routing_stats as llm_routing_stats
from DeepBl4nder.logging_setup import setup_logging

logger = logging.getLogger("DeepBl4nder.api")


class _RateLimitMiddleware:
    """Rate limiter mémoire simple : tokens bucket par clé (IP ou user)."""

    def __init__(self, app: FastAPI, max_requests: int = 60, window_seconds: int = 60) -> None:
        self._app = app
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = {}

    def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        return self._app(scope, receive, send)

    def is_rate_limited(self, key: str) -> bool:
        import time as _time
        now = _time.time()
        bucket = self._buckets.setdefault(key, [])
        cutoff = now - self._window
        bucket[:] = [t for t in bucket if t > cutoff]
        if len(bucket) >= self._max:
            return True
        bucket.append(now)
        return False


_rate_limit_buckets: dict[str, list[float]] = {}
_RATE_LIMIT_MAX = int(os.environ.get("DeepBl4nder_RATE_LIMIT_MAX", "60"))
_RATE_LIMIT_WINDOW = int(os.environ.get("DeepBl4nder_RATE_LIMIT_WINDOW", "60"))


def _check_rate_limit(request: Request) -> None:
    """Vérifie le rate limit par IP. Lève 429 si dépassé."""
    import time as _time
    client_ip = request.client.host if request.client else "unknown"
    key = f"global:{client_ip}"
    now = _time.time()
    bucket = _rate_limit_buckets.setdefault(key, [])
    cutoff = now - _RATE_LIMIT_WINDOW
    bucket[:] = [t for t in bucket if t > cutoff]
    if len(bucket) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    bucket.append(now)


def _default_secret_key() -> str:
    configured = os.environ.get("DeepBl4nder_SECRET_KEY")
    if configured:
        return configured
    logger.warning("DeepBl4nder_SECRET_KEY non définie — clé aléatoire (jetons perdus au redémarrage).")
    return secrets.token_hex(32)


def _default_org_name(full_name: str, email: str) -> str:
    """Nom d'organisation par défaut : nom complet, sinon le préfixe de l'email."""
    base = full_name.strip() or email.split("@")[0].title()
    return f"{base} Organization"


def _default_data_dir() -> str:
    return os.environ.get("DeepBl4nder_DATA_DIR", "data")


def _run_workdir(data_dir: str, production_id: str) -> Path:
    return Path(data_dir) / "runs" / production_id


def _artifact_type(name: str) -> str:
    if name.endswith(".py"):
        return "blender_script"
    if name.endswith(".json"):
        return "spec"
    if name.endswith((".mp4", ".mov", ".webm")):
        return "video"
    if name.endswith((".png", ".jpg", ".jpeg", ".exr", ".tiff")):
        return "image"
    if name.endswith((".wav", ".mp3", ".flac", ".ogg")):
        return "audio"
    return "artifact"


def _env_float(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _env_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


_PREVIEW_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm", ".mov")
_PREVIEW_IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _run_timeout_seconds() -> float | None:
    """Timeout global d'un run (0/absent = sans limite).

    ``DeepBl4nder_RUN_TIMEOUT`` en secondes. Sans lui, un run dont tous les
    fournisseurs LLM échouent peut rester bloqué en statut ``running``
    pendant de longues minutes (retries NOOA successives) — un erreur
    silencieuse pour l'utilisateur. Le timeout force l'échec proprement.
    """
    raw = os.environ.get("DeepBl4nder_RUN_TIMEOUT", "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        logger.warning("DeepBl4nder_RUN_TIMEOUT invalide (%r) — ignoré", raw)
        return None
    return None if value <= 0 else value


async def _launch_tracked_run(
    app: FastAPI,
    *,
    production_id: str,
    project_id: str,
    brief: str,
    workdir: Path,
) -> None:
    """Lance le pipeline en tâche de fond et maintient le statut worker à jour.

    Un timeout configurable (``DeepBl4nder_RUN_TIMEOUT``) met fin à un run
    qui n'avance plus (ex. tous les fournisseurs LLM en échec persistant) et
    le marque ``failed`` au lieu de le laisser bloqué en ``running``.
    """
    status: WorkerStatus = app.state.worker_status
    status.start(production_id)

    async def _pipeline() -> None:
        await run_production(
            production_id=production_id,
            project_id=project_id,
            brief=brief,
            workdir=workdir,
            bus=app.state.bus,
            session_factory=get_session_factory(),
            budget_limit=float(os.environ.get("DeepBl4nder_BUDGET", "1.0")),
        )

    timeout = _run_timeout_seconds()
    try:
        if timeout:
            await asyncio.wait_for(_pipeline(), timeout=timeout)
        else:
            await _pipeline()
        status.finish(production_id)
    except asyncio.TimeoutError:
        logger.warning("[run %s] dépassement du délai de %ss → marqué échec", production_id, timeout)
        status.finish(production_id, failed=True)
        _mark_production_failed(production_id, f"run dépassé le délai de {timeout}s (fournisseurs LLM indisponibles ?)")
    except asyncio.CancelledError:
        logger.warning("[run %s] tâche annulée (arrêt serveur ?)", production_id)
        status.finish(production_id, failed=True)
    except Exception:  # noqa: BLE001
        # JAMAIS silencieux : l'échec d'arrière-plan est tracé intégralement.
        logger.exception("[run %s] échec inattendu du pipeline", production_id)
        status.finish(production_id, failed=True)


def _mark_production_failed(production_id: str, message: str) -> None:
    """Marque une production en échec, indépendamment du tracker du run.

    Utilisé quand le run est interrompu hors de ``run_production`` (timeout) :
    le tracker interne n'étant pas notifié, on met la base à jour directement.
    """
    from datetime import datetime, timezone

    session = None
    try:
        session = get_session_factory()()
        production = session.get(Production, production_id)
        if production is not None and production.status in ("running", "queued", "revising"):
            production.status = "failed"
            production.error = message[:2000]
            production.finished_at = datetime.now(timezone.utc)
            production.updated_at = datetime.now(timezone.utc)
            session.commit()
    except Exception:  # noqa: BLE001 - ne masque jamais l'erreur d'origine
        logger.exception("[run %s] échec de la mise à jour failed en base", production_id)
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass


def _run_alembic_upgrade(url: str) -> None:
    """Exécute les migrations Alembic sur la base donnée."""
    import tempfile
    from pathlib import Path as _Path

    from alembic import command
    from alembic.config import Config as AlembicConfig

    alembic_dir = _Path(__file__).resolve().parent.parent.parent / "alembic"
    if not alembic_dir.is_dir():
        logger.debug("Répertoire alembic non trouvé, fallback sur create_all")
        return

    ini_path = alembic_dir.parent / "alembic.ini"
    if not ini_path.is_file():
        logger.debug("alembic.ini non trouvé, fallback sur create_all")
        return

    alembic_cfg = AlembicConfig(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", url)

    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations Alembic appliquées avec succès")
    except Exception:
        logger.exception("Échec des migrations Alembic — fallback sur create_all")
        raise


def create_app(
    database_url: str | None = None,
    secret_key: str | None = None,
    data_dir: str | None = None,
) -> FastAPI:
    """Fabrique l'application FastAPI avec son moteur SQLAlchemy."""
    setup_logging()
    url = database_url or os.environ.get("DeepBl4nder_DB", "DeepBl4nder.db")
    engine = create_engine_for(url)

    # Essayer Alembic en priorité ; fallback sur create_all (tests / dev)
    alembic_ok = False
    try:
        _run_alembic_upgrade(url)
        alembic_ok = True
    except Exception:
        logger.exception("Échec des migrations Alembic — fallback sur create_all")

    if not alembic_ok:
        logger.info("Création des tables via create_all (premier démarrage ou tests)")
        Base.metadata.create_all(engine)

    configure(engine, create_session_factory(engine), secret_key or _default_secret_key())

    app = FastAPI(
        title="DeepBl4nder API",
        description="AI-powered audiovisual production platform. Transform text prompts into complete animations/videos.",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    origins = [
        o.strip()
        for o in os.environ.get("DeepBl4nder_CORS_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    app.state.data_dir = data_dir or _default_data_dir()
    app.state.bus = AsyncEventBus()
    app.state.worker_status = WorkerStatus()

    _register_routes(app)
    return app


def _register_routes(app: FastAPI) -> None:

    @app.get("/api/health", tags=["health"])
    def health_check() -> dict[str, Any]:
        """Health check endpoint for load balancers and monitoring."""
        from DeepBl4nder import __version__ as ver
        return {"status": "ok", "version": ver, "timestamp": time.time()}

    @app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
    def register(payload: RegisterRequest, db: DbSession, request: Request) -> TokenResponse:
        _check_rate_limit(request)
        existing = db.scalar(select(User).where(User.email == payload.email))
        if existing is not None and existing.is_active:
            raise HTTPException(status_code=409, detail="email already registered")
        if existing is None:
            user = User(
                email=payload.email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
            )
            db.add(user)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=409, detail="email already registered")
        else:
            user = existing
            user.password_hash = hash_password(payload.password)
            user.full_name = payload.full_name
            user.is_active = True
        has_membership = db.scalar(select(Membership).where(Membership.user_id == user.id)) is not None
        if not has_membership:
            organization = Organization(name=_default_org_name(payload.full_name, payload.email), owner_id=user.id)
            db.add(organization)
            db.flush()
            db.add(Membership(user_id=user.id, organization_id=organization.id, role="owner"))
            db.add(Workspace(organization_id=organization.id, name="Default"))
        secret = get_secret_key()
        access = create_token(user.id, secret)
        refresh = create_refresh_token(user.id, secret)
        _store_refresh_token(db, user.id, refresh)
        return TokenResponse(access_token=access, refresh_token=refresh)

    @app.post("/api/auth/login", response_model=TokenResponse)
    def login(payload: LoginRequest, db: DbSession, request: Request) -> TokenResponse:
        _check_rate_limit(request)
        user = db.scalar(select(User).where(User.email == payload.email))
        if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
            raise HTTPException(status_code=401, detail="invalid credentials")
        secret = get_secret_key()
        access = create_token(user.id, secret)
        refresh = create_refresh_token(user.id, secret)
        _store_refresh_token(db, user.id, refresh)
        return TokenResponse(access_token=access, refresh_token=refresh)

    def _store_refresh_token(db: DbSession, user_id: str, refresh_token: str) -> None:
        """Stocke le hash du refresh token en base pour la révocation."""
        from datetime import timedelta
        db.add(RefreshToken(
            user_id=user_id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ))

    @app.post("/api/auth/refresh", response_model=TokenResponse)
    def refresh_token(payload: RefreshTokenRequest, db: DbSession, request: Request) -> TokenResponse:
        """Échange un refresh token contre de nouveaux access + refresh tokens (rotation)."""
        _check_rate_limit(request)
        secret = get_secret_key()
        payload_data = decode_token_full(payload.refresh_token, secret)
        if payload_data is None or payload_data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="invalid refresh token")
        user_id = payload_data.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="invalid refresh token")
        # Vérifier que le token existe en base et n'est pas révoqué
        token_hash = hash_token(payload.refresh_token)
        db_token = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
            )
        )
        if db_token is None:
            raise HTTPException(status_code=401, detail="refresh token revoked or not found")
        # Vérifier l'expiration
        if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="refresh token expired")
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="user not found or inactive")
        # Révoquer l'ancien refresh token (rotation)
        db_token.revoked = True
        # Générer de nouveaux tokens
        new_access = create_token(user.id, secret)
        new_refresh = create_refresh_token(user.id, secret)
        _store_refresh_token(db, user.id, new_refresh)
        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    @app.post("/api/auth/logout", status_code=204)
    def logout(payload: LogoutRequest, db: DbSession) -> None:
        """Révoque un refresh token (déconnexion)."""
        secret = get_secret_key()
        token_hash = hash_token(payload.refresh_token)
        db_token = db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if db_token is not None:
            db_token.revoked = True

    @app.get("/api/me", response_model=MeOut)
    def me(user: CurrentUser, db: DbSession) -> MeOut:
        memberships = db.scalars(
            select(Membership).where(Membership.user_id == user.id).order_by(Membership.organization_id)
        ).all()
        return MeOut(
            user=UserOut.model_validate(user),
            memberships=[MembershipOut(organization_id=m.organization_id, role=m.role) for m in memberships],
        )

    # ----- Organisations -----

    @app.get("/api/organizations", response_model=list[OrgOut])
    def list_organizations(user: CurrentUser, db: DbSession) -> list[OrgOut]:
        from sqlalchemy.orm import joinedload
        memberships = db.scalars(
            select(Membership)
            .options(joinedload(Membership.organization))
            .where(Membership.user_id == user.id)
            .order_by(Membership.organization_id)
        ).all()
        return [
            OrgOut(
                id=m.organization.id,
                name=m.organization.name,
                owner_id=m.organization.owner_id,
                created_at=m.organization.created_at,
                role=m.role,
            )
            for m in memberships
        ]

    @app.post("/api/organizations", response_model=OrgOut, status_code=201)
    def create_organization(payload: OrgCreate, user: CurrentUser, db: DbSession) -> OrgOut:
        organization = Organization(name=payload.name, owner_id=user.id)
        db.add(organization)
        db.flush()
        db.add(Membership(user_id=user.id, organization_id=organization.id, role="owner"))
        db.add(Workspace(organization_id=organization.id, name="Default"))
        return OrgOut(
            id=organization.id,
            name=organization.name,
            owner_id=organization.owner_id,
            created_at=organization.created_at,
            role="owner",
        )

    @app.get("/api/organizations/{organization_id}", response_model=OrgDetailOut)
    def get_organization_detail(
        organization_id: str,
        user: CurrentUser,
        db: DbSession,
    ) -> OrgDetailOut:
        from sqlalchemy.orm import joinedload
        organization = get_organization(db, organization_id)
        membership = require_membership(db, organization.id, user)
        require_role(membership, *ROLE_READ)
        memberships = db.scalars(
            select(Membership)
            .options(joinedload(Membership.user))
            .where(Membership.organization_id == organization.id)
        ).all()
        members: list[MemberOut] = []
        for m in memberships:
            if m.user is None:
                continue
            members.append(
                MemberOut(
                    user_id=m.user.id,
                    email=m.user.email,
                    full_name=m.user.full_name,
                    role=m.role,
                )
            )
        return OrgDetailOut(
            id=organization.id,
            name=organization.name,
            owner_id=organization.owner_id,
            created_at=organization.created_at,
            role=membership.role,
            members=members,
        )

    @app.get("/api/organizations/{organization_id}/members", response_model=list[MemberOut])
    def list_members(organization_id: str, user: CurrentUser, db: DbSession) -> list[MemberOut]:
        from sqlalchemy.orm import joinedload
        organization = get_organization(db, organization_id)
        membership = require_membership(db, organization.id, user)
        require_role(membership, *ROLE_READ)
        memberships = db.scalars(
            select(Membership)
            .options(joinedload(Membership.user))
            .where(Membership.organization_id == organization.id)
        ).all()
        members: list[MemberOut] = []
        for m in memberships:
            if m.user is None:
                continue
            members.append(
                MemberOut(
                    user_id=m.user.id,
                    email=m.user.email,
                    full_name=m.user.full_name,
                    role=m.role,
                )
            )
        return members

    @app.post("/api/organizations/{organization_id}/members", response_model=MemberOut, status_code=201)
    def add_member(
        organization_id: str,
        payload: MemberAdd,
        user: CurrentUser,
        db: DbSession,
    ) -> MemberOut:
        organization = get_organization(db, organization_id)
        membership = require_membership(db, organization.id, user)
        require_role(membership, *ROLE_MANAGE)
        member_user = db.scalar(select(User).where(User.email == payload.email))
        if member_user is None:
            member_user = User(
                email=payload.email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                is_active=False,
            )
            db.add(member_user)
            db.flush()
        existing = db.scalar(
            select(Membership).where(
                Membership.organization_id == organization.id,
                Membership.user_id == member_user.id,
            )
        )
        if existing is not None:
            existing.role = payload.role
            return MemberOut(
                user_id=member_user.id,
                email=member_user.email,
                full_name=member_user.full_name,
                role=existing.role,
            )
        db.add(Membership(user_id=member_user.id, organization_id=organization.id, role=payload.role))
        return MemberOut(
            user_id=member_user.id,
            email=member_user.email,
            full_name=member_user.full_name,
            role=payload.role,
        )

    # ----- Workspaces -----

    @app.get("/api/organizations/{organization_id}/workspaces", response_model=list[WorkspaceOut])
    def list_workspaces(organization_id: str, user: CurrentUser, db: DbSession) -> list[WorkspaceOut]:
        organization = get_organization(db, organization_id)
        membership = require_membership(db, organization.id, user)
        require_role(membership, *ROLE_READ)
        workspaces = db.scalars(
            select(Workspace).where(Workspace.organization_id == organization.id).order_by(Workspace.name)
        ).all()
        return [WorkspaceOut.model_validate(ws) for ws in workspaces]

    @app.post("/api/organizations/{organization_id}/workspaces", response_model=WorkspaceOut, status_code=201)
    def create_workspace(
        organization_id: str,
        payload: WorkspaceCreate,
        user: CurrentUser,
        db: DbSession,
    ) -> WorkspaceOut:
        organization = get_organization(db, organization_id)
        membership = require_membership(db, organization.id, user)
        require_role(membership, *ROLE_WRITE)
        workspace = Workspace(organization_id=organization.id, name=payload.name)
        db.add(workspace)
        db.flush()
        return WorkspaceOut.model_validate(workspace)

    # ----- Projets -----

    @app.get("/api/workspaces/{workspace_id}/projects", response_model=list[ProjectOut])
    def list_projects(workspace_id: str, user: CurrentUser, db: DbSession) -> list[ProjectOut]:
        workspace, membership = scoped_workspace(db, user, workspace_id)
        require_role(membership, *ROLE_READ)
        projects = db.scalars(
            select(Project).where(Project.workspace_id == workspace.id).order_by(Project.name)
        ).all()
        return [ProjectOut.model_validate(project) for project in projects]

    @app.post("/api/workspaces/{workspace_id}/projects", response_model=ProjectOut, status_code=201)
    def create_project(
        workspace_id: str,
        payload: ProjectCreate,
        user: CurrentUser,
        db: DbSession,
    ) -> ProjectOut:
        workspace, membership = scoped_workspace(db, user, workspace_id)
        require_role(membership, *ROLE_WRITE)
        project = Project(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            name=payload.name,
            description=payload.description,
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        return ProjectOut.model_validate(project)

    @app.get("/api/projects/{project_id}", response_model=ProjectOut)
    def get_project(project_id: str, user: CurrentUser, db: DbSession) -> ProjectOut:
        project, membership = scoped_project(db, user, project_id)
        require_role(membership, *ROLE_READ)
        return ProjectOut.model_validate(project)

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str, user: CurrentUser, db: DbSession) -> None:
        project, membership = scoped_project(db, user, project_id)
        require_role(membership, *ROLE_MANAGE)
        status: WorkerStatus = app.state.worker_status
        productions = db.scalars(select(Production).where(Production.project_id == project.id)).all()
        for production in productions:
            status.cancel_task(production.id)
            status.finish(production.id, failed=True)
            db.delete(production)
        db.delete(project)

    # ----- Productions -----

    @app.get("/api/projects/{project_id}/productions", response_model=list[ProductionOut])
    def list_productions(project_id: str, user: CurrentUser, db: DbSession) -> list[ProductionOut]:
        project, membership = scoped_project(db, user, project_id)
        require_role(membership, *ROLE_READ)
        productions = db.scalars(
            select(Production).where(Production.project_id == project.id).order_by(Production.created_at.desc())
        ).all()
        return [ProductionOut.model_validate(production) for production in productions]

    @app.post("/api/projects/{project_id}/productions", response_model=ProductionOut, status_code=201)
    def create_production(
        project_id: str,
        payload: ProductionCreate,
        user: CurrentUser,
        db: DbSession,
    ) -> ProductionOut:
        project, membership = scoped_project(db, user, project_id)
        require_role(membership, *ROLE_WRITE)
        production = Production(
            project_id=project.id,
            organization_id=project.organization_id,
            name=payload.name,
            brief=payload.brief,
            status="draft",
            created_by=user.id,
        )
        db.add(production)
        db.flush()
        return ProductionOut.model_validate(production)

    @app.get("/api/productions/{production_id}", response_model=ProductionOut)
    def get_production(production_id: str, user: CurrentUser, db: DbSession) -> ProductionOut:
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_READ)
        return ProductionOut.model_validate(production)

    @app.get("/api/productions/{production_id}/timeline", response_model=TimelineOut)
    def get_production_timeline(production_id: str, user: CurrentUser, db: DbSession) -> TimelineOut:
        from sqlalchemy.orm import selectinload
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_READ)
        sequences = db.scalars(
            select(Sequence)
            .options(
                selectinload(Sequence.scenes).selectinload(Scene.shots)
            )
            .where(Sequence.production_id == production.id)
            .order_by(Sequence.order_index)
        ).unique().all()
        seq_outs: list[SequenceOut] = []
        for seq in sequences:
            scene_outs: list[SceneOut] = []
            for scene in seq.scenes:
                shot_outs = [
                    ShotOut(
                        id=s.id,
                        index=s.index,
                        start=s.start,
                        end=s.end,
                        camera_summary=s.camera_summary,
                        action=s.action,
                        status=s.status,
                    )
                    for s in scene.shots
                ]
                scene_outs.append(SceneOut(
                    id=scene.id,
                    name=scene.name,
                    order_index=scene.order_index,
                    status=scene.status,
                    shots=shot_outs,
                ))
            seq_outs.append(SequenceOut(
                id=seq.id,
                name=seq.name,
                order_index=seq.order_index,
                scenes=scene_outs,
            ))
        return TimelineOut(production_id=production.id, sequences=seq_outs)

    @app.post("/api/productions/{production_id}/patches", response_model=PatchResponse)
    def create_patch(
        production_id: str,
        payload: PatchRequest,
        user: CurrentUser,
        db: DbSession,
    ) -> PatchResponse:
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_WRITE)
        
        import json
        import uuid
        from datetime import datetime, timezone
        
        # Store patch in database
        patch = Patch(
            id=uuid.uuid4().hex[:12],
            production_id=production.id,
            organization_id=production.organization_id,
            target=payload.target,
            old_value=json.dumps(payload.old_value) if payload.old_value is not None else "",
            new_value=json.dumps(payload.new_value),
            rationale=payload.rationale,
            author_id=user.id,
            applied=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(patch)
        
        # Publish event for real-time updates
        app.state.bus.publish_nowait({
            "type": "patch_created",
            "production_id": production.id,
            "patch_id": patch.id,
            "target": payload.target,
            "ts": datetime.now(timezone.utc).timestamp(),
        })
        
        return PatchResponse(
            patch_id=patch.id,
            status="pending",
            message="Patch stored and will be applied on next run",
        )

    # ----- Exécution du pipeline (Phase D) -----

    @app.post("/api/productions/{production_id}/run", response_model=ProductionOut, status_code=202)
    async def run_production_endpoint(
        production_id: str,
        user: CurrentUser,
        db: DbSession,
    ) -> ProductionOut:
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_WRITE)
        if production.status in ("queued", "running"):
            raise HTTPException(status_code=409, detail="production already running")
        workdir = _run_workdir(app.state.data_dir, production.id)
        production.status = "queued"
        production.error = ""
        db.commit()
        status: WorkerStatus = app.state.worker_status
        status.submit()
        task = asyncio.create_task(
            _launch_tracked_run(
                app,
                production_id=production.id,
                project_id=production.project_id,
                brief=production.brief,
                workdir=workdir,
            )
        )
        status.register_task(production.id, task)
        db.refresh(production)
        return ProductionOut.model_validate(production)

    @app.post("/api/productions/{production_id}/revision", response_model=ProductionOut, status_code=202)
    async def request_revision(
        production_id: str,
        payload: RevisionRequest,
        user: CurrentUser,
        db: DbSession,
    ) -> ProductionOut:
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_WRITE)
        if production.status in ("queued", "running"):
            raise HTTPException(status_code=409, detail="production already running")
        workdir = _run_workdir(app.state.data_dir, production.id)
        workdir.mkdir(parents=True, exist_ok=True)
        revision_doc = {
            "type": "revision_request",
            "target_step": payload.target_step,
            "comment": payload.comment,
            "requested_by": user.email,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "version_before": production.version,
        }
        spec_path = workdir / f"revision_request_{int(time.time())}.json"
        spec_path.write_text(json.dumps(revision_doc, ensure_ascii=False), encoding="utf-8")
        production.status = "revising"
        production.error = ""
        db.commit()
        app.state.bus.publish_nowait(
            {
                "type": "revision_requested",
                "production_id": production.id,
                "ts": time.time(),
                "target_step": payload.target_step,
                "revision": production.version,
                "comment": payload.comment,
            }
        )
        status: WorkerStatus = app.state.worker_status
        status.submit()
        task = asyncio.create_task(
            _launch_tracked_run(
                app,
                production_id=production.id,
                project_id=production.project_id,
                brief=production.brief,
                workdir=workdir,
            )
        )
        status.register_task(production.id, task)
        db.refresh(production)
        return ProductionOut.model_validate(production)

    @app.post("/api/productions/{production_id}/cancel", response_model=ProductionOut)
    def cancel_production(production_id: str, user: CurrentUser, db: DbSession) -> ProductionOut:
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_MANAGE)
        if production.status in ("completed", "cancelled", "failed"):
            raise HTTPException(status_code=409, detail=f"production is {production.status}")
        status: WorkerStatus = app.state.worker_status
        status.cancel_task(production.id)
        production.status = "cancelled"
        production.finished_at = datetime.now(timezone.utc)
        db.commit()
        status.finish(production.id)
        db.refresh(production)
        return ProductionOut.model_validate(production)

    @app.get("/api/productions/{production_id}/artifacts", response_model=list[ArtifactOut])
    def list_artifacts(production_id: str, user: CurrentUser, db: DbSession) -> list[ArtifactOut]:
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_READ)
        workdir = _run_workdir(app.state.data_dir, production.id)
        if not workdir.exists():
            return []
        artifacts: list[ArtifactOut] = []
        for path in sorted(workdir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(workdir).as_posix()
            artifacts.append(
                ArtifactOut(
                    name=path.name,
                    type=_artifact_type(path.name),
                    path=rel,
                    size=path.stat().st_size,
                )
            )
        return artifacts

    @app.get("/api/productions/{production_id}/artifacts/{path:path}")
    def download_artifact(production_id: str, path: str, user: CurrentUser, db: DbSession) -> FileResponse:
        """Télécharge un artifact par son chemin relatif (résolu dans le workdir)."""
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_READ)
        workdir = _run_workdir(app.state.data_dir, production.id).resolve()
        target = (workdir / path).resolve()
        if workdir != target and workdir not in target.parents:
            raise HTTPException(status_code=404, detail="artifact not found")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="artifact not found")
        return FileResponse(target, filename=Path(path).name)

    @app.delete("/api/productions/{production_id}/artifacts/{path:path}", status_code=204)
    def delete_artifact(production_id: str, path: str, user: CurrentUser, db: DbSession) -> None:
        """Supprime un artifact par son chemin relatif (résolu dans le workdir)."""
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_MANAGE)
        workdir = _run_workdir(app.state.data_dir, production.id).resolve()
        target = (workdir / path).resolve()
        if workdir != target and workdir not in target.parents:
            raise HTTPException(status_code=404, detail="artifact not found")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="artifact not found")
        target.unlink()

    @app.get("/api/productions/{production_id}/versions", response_model=ArtifactRecordsOut)
    def list_artifact_versions(
        production_id: str,
        user: CurrentUser,
        db: DbSession,
        type: str | None = None,
        name: str | None = None,
    ) -> ArtifactRecordsOut:
        """Liste l'historique des versions d'artifacts pour une production."""
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_READ)
        
        from sqlalchemy import select
        query = select(ArtifactRecord).where(ArtifactRecord.production_id == production.id)
        if type:
            query = query.where(ArtifactRecord.type == type)
        if name:
            query = query.where(ArtifactRecord.name == name)
        query = query.order_by(ArtifactRecord.created_at.desc())
        
        records = db.scalars(query).all()
        
        import json
        result = []
        for r in records:
            try:
                parents = json.loads(r.parent_ids) if r.parent_ids else []
            except json.JSONDecodeError:
                parents = []
            result.append(ArtifactRecordOut(
                id=r.id,
                type=r.type,
                name=r.name,
                version=r.version,
                path=r.path,
                sha256=r.sha256,
                status=r.status,
                cost=r.cost,
                parent_ids=parents,
                created_at=r.created_at,
            ))
        return ArtifactRecordsOut(records=result)

    @app.post("/api/artifacts/{artifact_id}/restore", response_model=PatchResponse)
    def restore_artifact_version(
        artifact_id: str,
        user: CurrentUser,
        db: DbSession,
    ) -> PatchResponse:
        """Restaure une version antérieure d'un artifact (crée un patch pour ré-appliquer)."""
        record = db.get(ArtifactRecord, artifact_id)
        if record is None:
            raise HTTPException(status_code=404, detail="artifact record not found")
        
        # Verify access via production
        production = db.get(Production, record.production_id)
        if production is None:
            raise HTTPException(status_code=404, detail="production not found")
        membership = require_membership(db, production.organization_id, user)
        require_role(membership, *ROLE_WRITE)
        
        # Create a patch to restore this version
        import uuid
        from datetime import datetime, timezone
        import json
        
        patch = Patch(
            id=uuid.uuid4().hex[:12],
            production_id=production.id,
            organization_id=production.organization_id,
            target="scene_spec",
            old_value="{}",  # current version
            new_value=json.dumps({"restore_from": artifact_id}),
            rationale=f"Restore artifact version {record.type}/{record.name} v{record.version}",
            author_id=user.id,
            applied=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(patch)
        db.commit()
        
        app.state.bus.publish_nowait({
            "type": "patch_created",
            "production_id": production.id,
            "patch_id": patch.id,
            "target": "scene_spec",
            "ts": datetime.now(timezone.utc).timestamp(),
        })
        
        return PatchResponse(
            patch_id=patch.id,
            status="pending",
            message=f"Restore patch created for {record.type}/{record.name} v{record.version}",
        )

    @app.get("/api/productions/{production_id}/preview")
    def production_preview(production_id: str, user: CurrentUser, db: DbSession) -> FileResponse:
        """Renvoie le premier rendu (image/vidéo) disponible pour la production."""
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_READ)
        workdir = _run_workdir(app.state.data_dir, production.id)
        if not workdir.exists():
            raise HTTPException(status_code=404, detail="no preview available")
        candidates = sorted(
            path
            for path in workdir.rglob("*")
            if path.is_file() and path.suffix.lower() in _PREVIEW_EXTENSIONS
        )
        images = [path for path in candidates if path.suffix.lower() in _PREVIEW_IMAGES]
        if not candidates:
            raise HTTPException(status_code=404, detail="no preview available")
        chosen = (images or candidates)[0]
        return FileResponse(chosen)

    @app.get("/api/worker", response_model=WorkerOut)
    def worker_status(user: CurrentUser, db: DbSession) -> WorkerOut:
        snapshot = app.state.worker_status.snapshot()
        rotation = "adaptive"
        routing: list[RoutingProviderOut] = []
        try:
            # routing_stats() module : ne construit PAS le routeur en effet de
            # bord d'un simple GET de statut (renvoie "uninitialized" sinon).
            stats = llm_routing_stats()
            if stats["pool"]:
                rotation = stats["rotation"]
                routing = [RoutingProviderOut(**prov) for prov in stats["providers"]]
        except Exception:  # noqa: BLE001 - routeur non configuré : on reste sans détail
            routing = []
        return WorkerOut(
            status=snapshot["status"],
            queue_depth=snapshot["queue_depth"],
            running=[WorkerRunOut(**run) for run in snapshot["running"]],
            processed=snapshot["processed"],
            failed=snapshot["failed"],
            last_heartbeat=snapshot["last_heartbeat"],
            rotation=rotation,
            routing=routing,
        )

    @app.post("/api/validate")
    def validate_script(payload: dict[str, Any], user: CurrentUser, db: DbSession) -> dict[str, Any]:
        """Valide un script bpy via AST (fail-closed policy)."""
        source = payload.get("source", "") if isinstance(payload, dict) else ""
        report: ValidationReport = ASTValidator().validate(source)
        return {
            "ok": report.ok,
            "errors": report.errors,
            "imports": report.imports,
        }

    @app.get("/api/usage", response_model=UsageOut)
    def usage(user: CurrentUser, db: DbSession) -> UsageOut:
        """Consommation et quotas de l'utilisateur courant (billing-ready)."""
        from sqlalchemy import func
        memberships = db.scalars(select(Membership).where(Membership.user_id == user.id)).all()
        organization_ids = [m.organization_id for m in memberships]
        if not organization_ids:
            return UsageOut(
                productions=0, runs=0, total_cost=0.0,
                quotas=UsageQuotas(
                    productions=_env_int("DeepBl4nder_QUOTA_PRODUCTIONS"),
                    cost=_env_float("DeepBl4nder_QUOTA_COST"),
                ),
            )
        total_cost = db.scalar(
            select(func.coalesce(func.sum(Production.cost), 0.0))
            .where(Production.organization_id.in_(organization_ids))
        )
        runs = db.scalar(
            select(func.count())
            .select_from(Production)
            .where(
                Production.organization_id.in_(organization_ids),
                Production.status != "draft",
            )
        )
        prod_count = db.scalar(
            select(func.count())
            .select_from(Production)
            .where(Production.organization_id.in_(organization_ids))
        )
        return UsageOut(
            productions=prod_count or 0,
            runs=runs or 0,
            total_cost=float(total_cost or 0.0),
            quotas=UsageQuotas(
                productions=_env_int("DeepBl4nder_QUOTA_PRODUCTIONS"),
                cost=_env_float("DeepBl4nder_QUOTA_COST"),
            ),
        )

    @app.get("/api/productions/{production_id}/events")
    async def production_events(
        production_id: str,
        user: CurrentUser,
        db: DbSession,
        after: int = 0,
    ) -> StreamingResponse:
        production, membership = scoped_production(db, user, production_id)
        require_role(membership, *ROLE_READ)
        bus: AsyncEventBus = app.state.bus
        queue = await bus.subscribe(production.id, after or None)
        return StreamingResponse(
            sse_event_stream(queue, bus.unsubscribe),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )


async def sse_event_stream(
    queue: asyncio.Queue[dict[str, object]],
    unsubscribe,
) -> AsyncGenerator[str, None]:
    """Génère le flux SSE depuis une file d'événements (heartbeat 15 s)."""
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
            except TimeoutError:
                yield "event: ping\n\n"
                continue
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    finally:
        await unsubscribe(queue)


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée `python -m DeepBl4nder.api.app --host ... --port ...`."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(prog="DeepBl4nder.api.app", description="API SaaS DeepBl4nder (FastAPI).")
    parser.add_argument("--host", default=os.environ.get("DeepBl4nder_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DeepBl4nder_PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("DeepBl4nder_DB", "DeepBl4nder.db"))
    args = parser.parse_args(argv)
    # Journal complet (console + fichier rotatif data/logs/DeepBl4nder.log) :
    # étapes pipeline, appels/votes/échecs LLM, découvertes de modèles.
    log_path = setup_logging()
    logger.info("Journal arrière-plan : %s", log_path)
    app = create_app(database_url=args.db)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
