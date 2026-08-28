"""Connexion SQLAlchemy pour le socle SaaS (SQLite par défaut).

Le socle utilise une base relationnelle locale (SQLite) pour les données
multi-tenant : users, organizations, membres, workspaces, projets et
productions. L'URL est surchargeable via `DeepBl4nder_DB` ou le paramètre
`database_url` de `create_app` (facilite la migration vers PostgreSQL).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from DeepBl4nder.api.state import get_session_factory


class Base(DeclarativeBase):
    """Base déclarative de tous les modèles du socle SaaS."""


def _as_sqlalchemy_url(url: str) -> str:
    """Accepte une URL complète ou un simple chemin de fichier SQLite.

    `DeepBl4nder.db` est converti en `sqlite:///<chemin absolu>` ; les URL
    avec schéma (ex. `sqlite:///x.db`, `postgresql://…`) passent telles quelles.
    """
    if "://" in url:
        return url
    return f"sqlite:///{Path(url).expanduser().resolve().as_posix()}"


def create_engine_for(url: str) -> Engine:
    """Crée un moteur SQLAlchemy pour l'URL donnée (SQLite inclus)."""
    from sqlalchemy import event as sa_event

    kwargs: dict[str, Any] = {}
    url = _as_sqlalchemy_url(url)
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        @sa_event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=True)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : session SQLAlchemy par requête.

    Auto-commit après yield ; rollback sur exception.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]
