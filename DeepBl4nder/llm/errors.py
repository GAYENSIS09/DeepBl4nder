"""Classification des erreurs LLM : classe stable, budget, re-tentative.

- ``_classify_error`` : traduit une exception litellm/HTTP en classe d'erreur
  stable (``rate_limit``, ``auth``, ``context``, ``model``, ``transient``,
  ``unknown``) + code HTTP.
- ``_afford_cap`` : budget de crédits restant annoncé par les fournisseurs
  (``gratis:``, ``COMPLETION:/...``) quand ``max_tokens`` a été refusé.
- ``_acall_with_budget_retry`` : refait un appel avec un ``max_tokens`` réduit
  si le fournisseur signale un budget insuffisant.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from nooa.unifiedllm import UnifiedLLM

logger = logging.getLogger("DeepBl4nder.llm.errors")
# Types litellm "déterministes" : la classe d'exception prime sur le message.
_LITELLM_DETERMINISTIC_MARKERS: tuple[tuple[str, str], ...] = (
    ("ratelimit", "rate_limit"),
    ("authentication", "auth"),
    ("contextwindow", "context"),
    ("permissiondenied", "auth"),
    ("forbidden", "auth"),
    ("notfound", "model"),
)

# Types litellm transitoires : tentés en dernier, car leur message peut révéler
# une cause sémantique (ex. Cloudflare remonte un modèle déprécié sous forme
# d'APIConnectionError — on ne doit pas le traiter comme une panne réseau).
_LITELLM_TRANSIENT_MARKERS: tuple[str, ...] = (
    "serviceunavailable",
    "internalservererror",
    "servererror",
    "apiconnection",
    "timeout",
)

# Codes HTTP fiables (portés par les exceptions litellm / httpx / requests).
# 400 est exclu : ambigu (contexte vs modèle vs quota) → les marqueurs texte
# tranchent. ``rate_limit`` couvre aussi 402 (billing/quotas, ex. OpenRouter).
_STATUS_TO_KIND: dict[int, str] = {
    401: "auth",
    402: "rate_limit",
    403: "auth",
    404: "model",
    408: "transient",
    429: "rate_limit",
    500: "transient",
    502: "transient",
    503: "transient",
    504: "transient",
}


def _classify_error(error: Exception) -> str:
    """Classe une erreur : rate_limit, model, auth, context ou transient.

    Hiérarchie de fiabilité :
    1. type d'exception litellm déterministe (indépendant du libellé) ;
    2. marqueurs texte — ils trahissent une cause sémantique même quand le
       fournisseur la remonte comme erreur de connexion ou 5xx ;
    3. code HTTP porté par l'exception (status_code) ;
    4. types litellm transitoires (timeout, connexion, 5xx génériques).

    ``rate_limit`` couvre aussi le quota/billing (ex. OpenRouter 402 : pas
    assez de crédits) : c'est un état du compte, pas un prompt trop long —
    le vote doit continuer avec les autres fournisseurs.
    """
    cls = type(error).__name__.lower()
    for marker, kind in _LITELLM_DETERMINISTIC_MARKERS:
        if marker in cls:
            return kind

    text = str(error).lower()
    if any(
        k in text
        for k in (
            "429",
            "rate limit",
            "rate_limit",
            "quota",
            "too many requests",
            "ratelimit",
            "402",
            "credits",
            "insufficient balance",
            "insufficient_quota",
            "insufficient quota",
            "requires more credits",
            "not enough credits",
            "openrouter_credits",
            "upgrade to a paid",
            "billing",
            "payment required",
            # Quotas quotidiens/mensuels Cloudflare Workers AI : le fournisseur
            # les remonte enveloppés dans une APIConnectionError ("… used up
            # your daily free allocation of 10,000 neurons …") — c'est un état
            # du compte, pas une panne réseau.
            "free allocation",
            "neurons",
            "workers paid plan",
        )
    ):
        return "rate_limit"
    if any(
        k in text
        for k in (
            "context length",
            "context_length",
            "context window",
            "maximum input tokens",
            "max input tokens",
            "max_input_tokens",
            "input length exceeded",
            "maximum context",
            "exceeds the maximum",
            "prompt is too long",
            "input is too long",
            "prompt too long",
            "token count exceeds",
        )
    ):
        return "context"
    if any(
        k in text
        for k in (
            "deprecated",
            "no longer available",
            "not found",
            "not_found",
            "404",
            "model_not_found",
            "model not found",
        )
    ):
        return "model"
    if any(k in text for k in ("401", "403", "authentication", "unauthorized", "forbidden", "invalid api key", "api key")):
        return "auth"

    status = getattr(error, "status_code", None)
    if isinstance(status, int) and not isinstance(status, bool):
        kind_by_status = _STATUS_TO_KIND.get(status)
        if kind_by_status is not None:
            return kind_by_status

    if any(marker in cls for marker in _LITELLM_TRANSIENT_MARKERS):
        return "transient"
    return "transient"


# Repli « budget crédits » : OpenRouter (entre autres) refuse une requête
# quand ``max_tokens`` dépasse ce que le solde peut couvrir — "You requested
# up to N tokens, but can only afford M." Plutôt que d'exclure un fournisseur
# sain, on retente UNE fois avec max_tokens=M. En dessous de
# ``_MIN_DOWNGRADE_TOKENS``, la sortie serait tronquée au point de produire du
# contenu invalide : on abandonne le fournisseur.
_AFFORD_RE = re.compile(r"can only afford (\d+)")
_MIN_DOWNGRADE_TOKENS = 1024


def _afford_cap(error: Exception) -> int | None:
    """Plafond de complétion annoncable par le fournisseur, sinon None."""
    if _classify_error(error) != "rate_limit":
        return None
    match = _AFFORD_RE.search(str(error).lower())
    return int(match.group(1)) if match else None


def _global_max_tokens() -> int | None:
    """Plafond global de complétion via ``DeepBl4nder_MAX_TOKENS`` (tokens).

    Permet de plafonner la sortie d'UN SEUL endroit pour respecter les
    capacités des fournisseurs gratuits (ex. OpenRouter plafonne la sortie du
    modèle free, Groq a un TPM bas). ``0``/absent = sans plafond global.
    """
    raw = os.environ.get("DeepBl4nder_MAX_TOKENS", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return None if value <= 0 else value


def _apply_global_max_tokens(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Plafonne ``max_tokens`` par la limite globale (si définie et plus basse)."""
    cap = _global_max_tokens()
    if cap is None:
        return kwargs
    requested = kwargs.get("max_tokens")
    if isinstance(requested, int) and not isinstance(requested, bool) and requested > cap:
        kwargs = {**kwargs, "max_tokens": cap}
    return kwargs


async def _acall_with_budget_retry(
    client: UnifiedLLM,
    messages: list[dict[str, Any]],
    tools: list[Any] | None,
    output_model: type[Any] | None,
    kwargs: dict[str, Any],
) -> tuple[Any, bool]:
    """Appel client avec repli budget : retourne (résultat, repli_effectué).

    Si l'appel échoue parce que le plafond de crédits est dépassé et que le
    plafond annoncé reste exploitable, retente une seule fois avec
    ``max_tokens`` réduit ; sinon relève l'erreur d'origine.
    """
    try:
        result = await client.acall(messages, tools=tools, output_model=output_model, **kwargs)
        return result, False
    except Exception as exc:  # noqa: BLE001
        cap = _afford_cap(exc)
        requested = kwargs.get("max_tokens")
        if (
            cap is not None
            and isinstance(requested, int)
            and not isinstance(requested, bool)
            and requested > cap >= _MIN_DOWNGRADE_TOKENS
        ):
            logger.warning(
                "LLM : max_tokens=%d refusé (budget crédits ≤ %d) → nouvelle tentative à max_tokens=%d",
                requested,
                cap,
                cap,
            )
            result = await client.acall(
                messages, tools=tools, output_model=output_model, **{**kwargs, "max_tokens": cap}
            )
            return result, True
        raise
