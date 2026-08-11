"""Sécurité : hachage des mots de passe (PBKDF2-HMAC-SHA256) et JWT HS256.

Les mots de passe ne sont jamais stockés en clair. Les jetons sont signés
HMAC-SHA256 avec une clé secrète (`DEEPBLENDER_SECRET_KEY`). Aucun secret
ne transite par le frontend ni par les logs.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

import jwt

_PBKDF2_ITERATIONS = 200_000
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hache un mot de passe avec un sel aléatoire (format `<salt_hex>$<digest_hex>`)."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Vérifie un mot de passe contre le hachage stocké (comparaison à temps constant)."""
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user_id: str, secret: str, ttl_hours: int = 24) -> str:
    """Crée un jeton JWT HS256 portant le `sub` = user_id."""
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + ttl_hours * 3600}
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_token(token: str, secret: str) -> str | None:
    """Décode un jeton et renvoie le `sub` (user_id), ou None si invalide/expiré."""
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        sub = payload.get("sub")
        return sub if isinstance(sub, str) else None
    except jwt.PyJWTError:
        return None
