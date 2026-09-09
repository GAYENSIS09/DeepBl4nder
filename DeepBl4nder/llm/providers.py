"""Registre des fournisseurs LLM cloud : définition, disponibilité, pool configuré.

Ce module n'a aucune dépendance vers les autres modules du package : c'est la
base. ``PROVIDERS`` (en dur ci-dessous) décrit chaque fournisseur ; les
fonctions ``configured_providers`` / ``set_configured_providers`` exposent le
pool restreint choisi par l'utilisateur (env ``DeepBl4nder_LLM_PROVIDERS``,
sinon clé ``provider_ids`` du fichier ``~/.deepbl4nder/llm.json``).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("DeepBl4nder.llm.providers")
@dataclass(frozen=True)
class LLMProvider:
    """Fournisseur LLM : clé d'API, base URL et modèles, en dur dans ``PROVIDERS``."""

    id: str
    api_key_env: str
    base_url: str
    models: tuple[str, ...]
    # URL envoyée à litellm à l'appel. None = litellm connaît l'URL officielle
    # (gemini/groq/openrouter/cloudflare). À définir pour les fournisseurs
    # OpenAI-compatibles servis sur un hôte non officiel (ex. NVIDIA) où le
    # préfixe litellm ``openai/`` exige une base explicite.
    litellm_api_base: str | None = None

    def default_model(self) -> str:
        """Premier modèle disponible (seul modèle actif de ce fournisseur)."""
        return self.models[0]

    def model(self) -> str:
        """Modèle actif : fixé dans le registre (plus de surcharge .env)."""
        return self.default_model()

    def api_key(self) -> str | None:
        """Clé d'API dédiée (seule lecture d'environnement du module)."""
        return os.getenv(self.api_key_env)

    def is_available(self) -> bool:
        """Un fournisseur est utilisable s'il a sa clé dédiée."""
        return bool(self.api_key())

    def api_base(self) -> str | None:
        """URL d'appel litellm : ``litellm_api_base`` si défini, sinon None
        (litellm connaît l'URL officielle du fournisseur)."""
        return self.litellm_api_base

    def resolved_base_url(self) -> str:
        """Base URL effective, placeholders substitués (ex. ``ACCOUNT_ID`` cloudflare).

        Cloudflare exige l'identifiant de compte dans l'URL ; litellm le lit
        aussi à l'appel via ``CLOUDFLARE_ACCOUNT_ID``, cette méthode sert à
        l'affichage (config / stats) sans placeholder brut.
        """
        custom = self.api_base()
        if custom:
            return custom
        if "ACCOUNT_ID" in self.base_url:
            return self.base_url.replace("ACCOUNT_ID", os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
        return self.base_url

    def config(self) -> dict[str, Any]:
        """Résumé de configuration (sans exposer la clé)."""
        return {
            "id": self.id,
            "base_url": self.resolved_base_url(),
            "model": self.model(),
            "api_key_configured": bool(self.api_key()),
        }


PROVIDERS: dict[str, LLMProvider] = {
    "gemini": LLMProvider(
        id="gemini",
        api_key_env="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        models=(
            "gemini/gemini-3.6-flash",
            "gemini/gemini-3.5-flash",
            "gemini/gemini-2.5-pro",
        ),
    ),
    "groq": LLMProvider(
        id="groq",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        # Modèles vérifiés actifs sur l'API Groq (2026) — llama-3.x décommissionnés.
        models=(
            "groq/openai/gpt-oss-120b",
            "groq/qwen/qwen3.6-27b",
            "groq/groq/compound-mini",
        ),
    ),
    "nvidia": LLMProvider(
        id="nvidia",
        api_key_env="NVIDIA_API_KEY",
        base_url="https://integrate.api.nvidia.com/v1",
        # API NIM historique (fonctions ``nvidia_nim/``) fermée : sur les
        # comptes récents elle répond 404 "Function not found for account"
        # (vérifié en direct 2026-09). On route l'endpoint OpenAI-compatible
        # integrate.api.nvidia.com avec les modèles actuels du
        # catalogue build.nvidia.com : nemotron-3.5-lightning (rapide, fiable),
        # nemotron-3-ultra, kimi-k3 puis deepseek-v4 (plus lent).
        # Préfixe ``openai/`` + ``litellm_api_base`` = endpoint OpenAI standard.
        litellm_api_base="https://integrate.api.nvidia.com/v1",
        models=(
            "openai/nvidia/nemotron-3.5-lightning-30b-a3b",
            "openai/nvidia/nemotron-3-ultra-550b-a55b",
            "openai/moonshotai/kimi-k3",
            "openai/deepseek-ai/deepseek-v4-pro-0813",
        ),
    ),
    "openrouter": LLMProvider(
        id="openrouter",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        models=(
            "openrouter/meta-llama/llama-3.3-70b-instruct",
            "openrouter/anthropic/claude-3.5-sonnet",
            "openrouter/openai/gpt-4o-mini",
        ),
    ),
    "cloudflare": LLMProvider(
        id="cloudflare",
        api_key_env="CLOUDFLARE_API_KEY",
        base_url="https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/v1",
        models=(
            "cloudflare/@cf/google/gemma-4-26b-a4b-it",
            "cloudflare/@cf/meta/llama-3.3-70b-instruct",
        ),
    ),
}


def get_provider(provider_id: str) -> LLMProvider:
    """Fournisseur du registre, avec une erreur claire si l'id est inconnu."""
    if provider_id not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Fournisseur LLM inconnu : {provider_id!r}. Disponibles : {available}.")
    return PROVIDERS[provider_id]

# ------------------------------------------------------------------ pool configuré
# Fichier de config utilisateur partagé (mêmes conventions que l'ex-model_registry) :
# ~/.deepbl4nder/llm.json, ou répertoire DeepBl4nder_CONFIG_DIR si défini.

_config_cache: dict[str, Any] | None = None
_config_mtime: float | None = None


def _config_path() -> Path:
    base = os.environ.get("DeepBl4nder_CONFIG_DIR")
    root = Path(base) if base else Path.home() / ".deepbl4nder"
    return root / "llm.json"


def _load_user_config() -> dict[str, Any]:
    """Config utilisateur persistée (cache par mtime) : ``provider_ids``, etc."""
    global _config_cache, _config_mtime
    path = _config_path()
    try:
        mtime = path.stat().st_mtime
        if _config_cache is not None and mtime == _config_mtime:
            return _config_cache
        raw = json.loads(path.read_text(encoding="utf-8"))
        data = raw if isinstance(raw, dict) else {}
        _config_cache = data
        _config_mtime = mtime
        return _config_cache
    except FileNotFoundError:
        _config_cache = {}
        _config_mtime = None
        return _config_cache
    except json.JSONDecodeError as exc:
        logger.warning("Config LLM invalide (%s) : %s", path, exc)
        _config_cache = {}
        _config_mtime = None
        return _config_cache
    except OSError as exc:
        logger.debug("Config LLM illisible (%s) : %s", path, exc)
        _config_cache = {}
        _config_mtime = None
        return _config_cache


def _env_provider_ids() -> list[str]:
    """Pool par variable d'environnement (priorité sur le fichier)."""
    for var in ("DeepBl4nder_LLM_PROVIDERS", "LLM_PROVIDERS"):
        raw = os.environ.get(var, "").strip()
        if raw:
            return [pid.strip() for pid in raw.split(",") if pid.strip()]
    return []


def _unique(ids: list[str]) -> list[str]:
    """Dédoublonne tout en écartant les ids hors registre (ordre préservé)."""
    seen: set[str] = set()
    out: list[str] = []
    for pid in ids:
        if pid in PROVIDERS and pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out


def configured_providers() -> list[str]:
    """Ids du pool restreint : env ``DeepBl4nder_LLM_PROVIDERS``, sinon fichier.

    Vide = « tous les fournisseurs disponibles » (décision du routeur).
    """
    configured = _env_provider_ids()
    if not configured:
        stored = _load_user_config().get("provider_ids")
        if isinstance(stored, list):
            configured = [str(pid) for pid in stored]
    return _unique(configured)


def set_configured_providers(provider_ids: list[str]) -> None:
    """Persiste le pool restreint (ids déjà validés par l'appelant)."""
    valid = _unique(provider_ids)
    data = _load_user_config()
    data["provider_ids"] = valid
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    global _config_cache, _config_mtime  # noqa: PLW0603 - cache volontaire
    _config_cache = data
    _config_mtime = path.stat().st_mtime


def reset_providers_config() -> None:
    """Recharge la config persistée (tests)."""
    global _config_cache, _config_mtime  # noqa: PLW0603 - cache volontaire
    _config_cache = None
    _config_mtime = None
