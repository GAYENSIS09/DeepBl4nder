"""Utilitaires partagés pour le domaine métier."""

from __future__ import annotations

from uuid import uuid4


def new_id() -> str:
    """Génère un identifiant unique court (hex)."""
    return uuid4().hex
