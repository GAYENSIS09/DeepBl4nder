"""CachePlugin : cache Redis pour les appels LLM et resultats.

Utilise Redis pour le cache distribue, le pub/sub pour les evenements,
et les queues pour les taches longues.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from deepblender.plugins.base import Plugin

logger = logging.getLogger("deepblender.plugins.cache")


@dataclass
class CachePlugin(Plugin):
    """Cache Redis avec fallback in-memory."""

    name: str = "cache"
    description: str = "Cache distribue Redis avec fallback in-memory."
    _redis_client: Any = field(default=None, repr=False)
    _memory_cache: dict[str, tuple[Any, float]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialise la connexion Redis si configuree."""
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            self._redis_client.ping()
            logger.info("Redis connecte: %s", redis_url)
        except Exception as exc:
            logger.warning("Redis indisponible (%s), fallback in-memory", exc)
            self._redis_client = None

    def available(self) -> bool:
        return True  # Fallback in-memory toujours disponible

    def get(self, key: str) -> Any | None:
        """Recupere une valeur du cache."""
        if self._redis_client:
            try:
                raw = self._redis_client.get(f"db:cache:{key}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass

        import time
        entry = self._memory_cache.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.time() > expiry:
            self._memory_cache.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Stocke une valeur dans le cache avec TTL."""
        if self._redis_client:
            try:
                self._redis_client.setex(
                    f"db:cache:{key}", ttl, json.dumps(value, default=str)
                )
                return
            except Exception:
                pass

        import time
        self._memory_cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """Supprime une entree du cache."""
        if self._redis_client:
            try:
                self._redis_client.delete(f"db:cache:{key}")
            except Exception:
                pass
        self._memory_cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Supprime toutes les entrees avec un prefixe donne."""
        count = 0
        if self._redis_client:
            try:
                keys = self._redis_client.keys(f"db:cache:{prefix}*")
                if keys:
                    count = self._redis_client.delete(*keys)
            except Exception:
                pass

        keys_to_delete = [k for k in self._memory_cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._memory_cache[k]
            count += 1
        return count

    def publish(self, channel: str, message: dict[str, Any]) -> None:
        """Publie un message sur un canal Redis (pub/sub)."""
        if self._redis_client:
            try:
                self._redis_client.publish(channel, json.dumps(message, default=str))
            except Exception:
                pass

    def subscribe(self, channel: str) -> Any:
        """S'abonne a un canal Redis (pub/sub)."""
        if self._redis_client:
            try:
                pubsub = self._redis_client.pubsub()
                pubsub.subscribe(channel)
                return pubsub
            except Exception:
                pass
        return None

    def queue_task(self, queue: str, task: dict[str, Any]) -> None:
        """Ajoute une tache a une file Redis."""
        if self._redis_client:
            try:
                self._redis_client.rpush(f"db:queue:{queue}", json.dumps(task, default=str))
            except Exception:
                pass

    def dequeue_task(self, queue: str, timeout: int = 0) -> dict[str, Any] | None:
        """Retire une tache d'une file Redis."""
        if self._redis_client:
            try:
                result = self._redis_client.blpop(f"db:queue:{queue}", timeout=timeout)
                if result:
                    return json.loads(result[1])
            except Exception:
                pass
        return None
