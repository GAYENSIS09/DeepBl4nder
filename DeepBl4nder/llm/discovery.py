"""Découverte dynamique des modèles : GET /models compatible OpenAI par fournisseur.

Chaque fournisseur est interrogé au démarrage du routeur ; les candidats bruts
sont ensuite filtrés par les règles de ``selection``. Un échec de listing
réseau garde la liste statique du registre (jamais d'exception).
"""

from __future__ import annotations

import logging
import re

import httpx

from .providers import LLMProvider

logger = logging.getLogger("DeepBl4nder.llm.discovery")
# Routes de listing par fournisseur : (suffixe, clé du tableau, champ id).
# La plupart exposent GET /models compatible OpenAI. Préfixe spécial
# ``ROOT:`` = chemin relatif à la racine API (base amputée de « /ai/v1 ») :
# le listing Cloudflare vit sous /client/v4/accounts/{id}/ai/models/search,
# alors que GET …/ai/v1/models répond 405.
_DISCOVERY_ROUTES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "cloudflare": (
        ("ROOT:/ai/models/search", "result", "name"),
        ("/models", "data", "id"),
    ),
}
_DEFAULT_DISCOVERY_ROUTE = (("/models", "data", "id"),)


def discover_models(provider: LLMProvider, timeout: float = 6.0) -> tuple[str, ...] | None:
    """Liste brute des modèles annoncés par le fournisseur.

    Essaie les routes de listing connues (compatible OpenAI en général,
    ``/ai/models/search`` pour Cloudflare). Retourne ``None`` en cas d'échec
    (réseau, clé, format) — jamais d'exception : la liste statique reste le
    filet de sécurité.
    """
    base = provider.resolved_base_url().rstrip("/")
    api_root = re.sub(r"/ai/v1$", "", base)
    headers: dict[str, str] = {}
    api_key = provider.api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    routes = _DISCOVERY_ROUTES.get(provider.id, _DEFAULT_DISCOVERY_ROUTE)
    last_error: Exception | None = None
    for suffix, collection_key, id_field in routes:
        if suffix.startswith("ROOT:"):
            url = f"{api_root}{suffix[len('ROOT:'):]}"
        else:
            url = f"{base}{suffix}"
        try:
            response = httpx.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - on essaie la route suivante
            last_error = exc
            logger.debug("Listing %s via %s impossible (%s)", provider.id, url, exc)
            continue
        items = payload.get(collection_key, [])
        ids = [
            str(item.get(id_field))
            for item in items
            if isinstance(item, dict) and item.get(id_field)
        ]
        logger.debug("Modèles bruts %s via %s (%d) : %s", provider.id, suffix, len(ids), ids)
        if ids:
            return tuple(ids)
    if last_error is not None:
        logger.warning(
            "Découverte des modèles %s impossible (%s : %s) → liste statique.",
            provider.id,
            type(last_error).__name__,
            str(last_error)[:160],
        )
    return None
