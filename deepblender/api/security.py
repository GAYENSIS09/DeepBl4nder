"""Sécurité : hachage des mots de passe (PBKDF2-HMAC-SHA256) et JWT HS256.

Les mots de passe ne sont jamais stockés en clair. Les jetons sont signés
HMAC-SHA256 avec une clé secrète (`DEEPBLENDER_SECRET_KEY`). Aucun secret
ne transite par le frontend ni par les logs.

Support des refresh tokens avec rotation et révocation.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

import jwt

_PBKDF2_ITERATIONS = 200_000
_ALGORITHM = "HS256"

# Token TTLs
ACCESS_TOKEN_TTL_HOURS = 1
REFRESH_TOKEN_TTL_DAYS = 7


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


def create_token(user_id: str, secret: str, ttl_hours: int = ACCESS_TOKEN_TTL_HOURS) -> str:
    """Crée un jeton d'accès JWT HS256 (durée courte, 1h par défaut)."""
    now = int(time.time())
    jti = secrets.token_hex(8)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ttl_hours * 3600,
        "type": "access",
        "jti": jti,
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def create_refresh_token(user_id: str, secret: str) -> str:
    """Crée un refresh token JWT HS256 (durée longue, 7 jours)."""
    now = int(time.time())
    jti = secrets.token_hex(8)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL_DAYS * 86400,
        "type": "refresh",
        "jti": jti,
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_token(token: str, secret: str, expected_type: str | None = None) -> str | None:
    """Décode un jeton et renvoie le `sub` (user_id), ou None si invalide/expiré.

    Si `expected_type` est fourni, vérifie que le claim `type` correspond.
    """
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        if expected_type is not None:
            token_type = payload.get("type")
            if token_type != expected_type:
                return None
        sub = payload.get("sub")
        return sub if isinstance(sub, str) else None
    except jwt.PyJWTError:
        return None


def decode_token_full(token: str, secret: str) -> dict | None:
    """Décode un jeton et renvoie le payload complet, ou None si invalide."""
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None


def hash_token(token: str) -> str:
    """Hache un token avec SHA-256 pour le stockage en base."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
