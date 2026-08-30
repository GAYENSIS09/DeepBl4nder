"""Prompt Cache Manager : gestion intelligente du cache KV pour les prompts.

Étape 3 du pipeline de gestion de contexte avancée.
Optimise les appels LLM en maximisant les hits du KV cache côté provider.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """Entrée de cache pour un bloc de contexte."""
    key: str
    content_hash: str
    value: str
    prefix: bool
    tokens_est: int
    last_used: float = field(default_factory=time.time)
    hit_count: int = 0


@dataclass
class CacheStats:
    """Statistiques du cache."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    entries_count: int = 0
    total_tokens_cached: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests * 100


class PromptCacheManager:
    """Étape 3: Gestion intelligente du cache KV.

    Stratégie:
    - PREFIX (stable): system_prompt, available_skills, domain_schema
      → Ces blocs changent rarement, maximiser le KV cache
    - SUFFIX (volatile): skill_* chargés, dynamic_context, history
      → Re-calculé à chaque tour, pas de cache KV possible

    Le KV cache côté provider fonctionne ainsi:
    - Si le préfixe est identique → réutiliser les KV déjà calculés
    - Seul le suffixe change → calcul incremental
    - Plus le préfixe est long et stable → plus l'économie est grande
    """

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._prefix_blocks: list[str] = []  # Ordre des blocs prefix
        self._last_prefix_hash: str | None = None

    def _content_hash(self, value: str) -> str:
        """Hash du contenu pour détection de changement."""
        return hashlib.md5(value.encode("utf-8")).hexdigest()[:16]

    def _estimate_tokens(self, text: str) -> int:
        """Estimation tokens (1 token ≈ 4 chars)."""
        return len(text) // 4 if text else 0

    def register_block(self, key: str, value: str, prefix: bool) -> CacheEntry:
        """Enregistre un bloc dans le cache.

        Args:
            key: Clé du bloc (ex: "system_prompt", "skill_storytelling").
            value: Contenu du bloc.
            prefix: True si bloc prefix (stable), False si suffix (volatile).

        Returns:
            L'entrée de cache créée/mise à jour.
        """
        content_hash = self._content_hash(value)
        tokens = self._estimate_tokens(value)

        if key in self._entries:
            entry = self._entries[key]
            entry.content_hash = content_hash
            entry.value = value
            entry.prefix = prefix
            entry.tokens_est = tokens
            entry.last_used = time.time()
        else:
            entry = CacheEntry(
                key=key,
                content_hash=content_hash,
                value=value,
                prefix=prefix,
                tokens_est=tokens,
            )
            self._entries[key] = entry

        if prefix and key not in self._prefix_blocks:
            self._prefix_blocks.append(key)

        self._stats.entries_count = len(self._entries)
        self._stats.total_tokens_cached = sum(e.tokens_est for e in self._entries.values())

        return entry

    def has_changed(self, key: str, value: str) -> bool:
        """Vérifie si un bloc a changé depuis la dernière mise en cache.

        Args:
            key: Clé du bloc.
            value: Nouvelle valeur.

        Returns:
            True si le contenu a changé.
        """
        if key not in self._entries:
            return True
        return self._entries[key].content_hash != self._content_hash(value)

    def compute_prefix_hash(self) -> str:
        """Calcule le hash du préfixe complet (tous les blocs prefix).

        Returns:
            Hash du préfixe, ou None si pas de blocs prefix.
        """
        if not self._prefix_blocks:
            return ""

        parts = []
        for key in self._prefix_blocks:
            if key in self._entries:
                entry = self._entries[key]
                parts.append(f"{key}:{entry.content_hash}")

        return "|".join(parts)

    def is_prefix_stable(self) -> bool:
        """Vérifie si le préfixe est identique au dernier appel.

        Returns:
            True si le préfixe n'a pas changé (cache hit potentiel).
        """
        current_hash = self.compute_prefix_hash()
        if current_hash == self._last_prefix_hash:
            return True
        return False

    def mark_prefix_used(self) -> None:
        """Marque le préfixe courant comme utilisé (après appel LLM réussi)."""
        self._last_prefix_hash = self.compute_prefix_hash()

    def on_request(self, is_hit: bool) -> None:
        """Enregistre un appel LLM (hit ou miss).

        Args:
            is_hit: True si le KV cache a été réutilisé.
        """
        self._stats.total_requests += 1
        if is_hit:
            self._stats.cache_hits += 1
        else:
            self._stats.cache_misses += 1

    def get_stats(self) -> CacheStats:
        """Retourne les statistiques du cache."""
        return self._stats

    def get_cache_efficiency(self) -> dict[str, Any]:
        """Retourne un rapport d'efficacité du cache."""
        prefix_tokens = sum(
            self._entries[k].tokens_est
            for k in self._prefix_blocks
            if k in self._entries
        )
        suffix_tokens = sum(
            e.tokens_est for k, e in self._entries.items()
            if not e.prefix
        )

        return {
            "total_entries": len(self._entries),
            "prefix_blocks": len(self._prefix_blocks),
            "prefix_tokens": prefix_tokens,
            "suffix_tokens": suffix_tokens,
            "total_tokens": prefix_tokens + suffix_tokens,
            "hit_rate": round(self._stats.hit_rate, 1),
            "total_requests": self._stats.total_requests,
            "cache_hits": self._stats.cache_hits,
            "prefix_stable": self.is_prefix_stable(),
        }

    def invalidate(self, key: str) -> None:
        """Invalide une entrée spécifique."""
        if key in self._entries:
            del self._entries[key]
            if key in self._prefix_blocks:
                self._prefix_blocks.remove(key)

    def invalidate_all(self) -> None:
        """Invalide tout le cache."""
        self._entries.clear()
        self._prefix_blocks.clear()
        self._last_prefix_hash = None
        self._stats = CacheStats()


# Singleton
_default_cache: PromptCacheManager | None = None


def get_prompt_cache() -> PromptCacheManager:
    """Retourne le gestionnaire de cache par défaut."""
    global _default_cache
    if _default_cache is None:
        _default_cache = PromptCacheManager()
    return _default_cache


def reset_prompt_cache() -> None:
    """Reset le cache (utile pour les tests)."""
    global _default_cache
    _default_cache = None
