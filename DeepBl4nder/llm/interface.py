"""Interface unifiée LLM pour les agents — remplace l'ancien LLMRouter.

Fournit ``build_llm()`` et ``LLMClient`` pour un usage transparent
par les agents existants. Gère automatiquement la classification
des tâches, la sélection de modèle et l'escalade en cascade.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from DeepBl4nder.llm.cascade import CascadeRouter
from DeepBl4nder.llm.client import LocalLLMClient
from DeepBl4nder.llm.classifier import TaskClassifier
from DeepBl4nder.llm.server import ModelServer

logger = logging.getLogger("DeepBl4nder.llm.interface")

# ── Singleton partagé ────────────────────────────────────────────────────

_client: LLMClient | None = None


class LLMClient:
    """Interface unifiée pour les agents — remplace l'ancien LLMRouter.

    Usage::

        client = LLMClient()
        result = await client.acall(messages=[...], tools=[...])
    """

    def __init__(
        self,
        server: ModelServer | None = None,
        classifier: TaskClassifier | None = None,
        cascade: CascadeRouter | None = None,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        self._server = server or ModelServer(host=host, port=port)
        self._classifier = classifier or TaskClassifier()
        self._cascade = cascade or CascadeRouter(self._classifier)
        self._client: LocalLLMClient | None = None
        self._max_escalations = 2

    def _get_client(self) -> LocalLLMClient:
        """Client HTTP lazy."""
        if self._client is None:
            self._client = LocalLLMClient(base_url=self._server.base_url)
        return self._client

    async def acall(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type | None = None,
        **kwargs: Any,
    ) -> Any:
        """Appel principal — les agents appellent cette méthode.

        1. Classifie la tâche
        2. Sélectionne le modèle optimal
        3. Appelle le serveur
        4. Escalade en cas d'échec
        """
        # Extraire le texte de la dernière tâche
        task_text = ""
        if messages:
            last = messages[-1]
            task_text = last.get("content", "") if isinstance(last, dict) else str(last)

        # Classification et sélection
        category = self._cascade.classify(task_text, messages)
        model = self._cascade.select_model(category)

        logger.debug(
            "LLM call : catégorie=%s, modèle=%s, messages=%d",
            category.value, model.id, len(messages),
        )

        # Assurer que le serveur tourne avec le bon modèle
        await self._server.ensure_model(model)

        # Normaliser les outils au format OpenAI
        openai_tools = self._normalize_tools(tools) if tools else None

        # Appel avec escalation
        last_error: Exception | None = None
        for attempt in range(self._max_escalations + 1):
            try:
                client = self._get_client()
                result = await client.chat_completion(
                    messages=messages,
                    tools=openai_tools,
                    **kwargs,
                )

                # Vérifier la qualité de la réponse
                if self._is_response_valid(result, output_model):
                    self._cascade.record_outcome(model.id, True)
                    return self._parse_response(result, output_model)

                # Réponse invalide → escalader
                self._cascade.record_outcome(model.id, False)
                next_model = self._cascade.escalate(model, category)
                if next_model is None:
                    # Pas d'escalade possible, retourner la réponse telle quelle
                    return self._parse_response(result, output_model)

                model = next_model
                await self._server.ensure_model(model)
                logger.info("Escalade vers %s (réponse invalide)", model.id)

            except Exception as exc:  # noqa: BLE001
                self._cascade.record_outcome(model.id, False)
                last_error = exc
                logger.warning("Appel LLM échoué (%s) : %s", model.id, exc)

                next_model = self._cascade.escalate(model, category)
                if next_model is None:
                    raise RuntimeError(
                        f"Tous les modèles ont échoué. Dernière erreur : {exc}"
                    ) from exc

                model = next_model
                await self._server.ensure_model(model)

        # Ne devrait jamais arriver ici
        raise last_error or RuntimeError("Aucune réponse du serveur LLM")

    def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any] | None = None,
        output_model: type | None = None,
        **kwargs: Any,
    ) -> Any:
        """Version synchrone de acall."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.acall(messages, tools=tools, output_model=output_model, **kwargs),
                )
                return future.result(timeout=300)

        return asyncio.run(
            self.acall(messages, tools=tools, output_model=output_model, **kwargs)
        )

    def _normalize_tools(self, tools: list[Any]) -> list[dict[str, Any]]:
        """Convertit les outils NOOA/format divers en format OpenAI."""
        normalized = []
        for tool in tools:
            if isinstance(tool, dict):
                # Déjà au bon format
                if "type" in tool and "function" in tool:
                    normalized.append(tool)
                # Format NOOA: wrapper en tool OpenAI
                elif "name" in tool:
                    normalized.append({
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                        },
                    })
                else:
                    normalized.append(tool)
            else:
                # Objet avec attr name/description
                name = getattr(tool, "name", None) or getattr(tool, "__name__", "unknown")
                desc = getattr(tool, "description", "")
                normalized.append({
                    "type": "function",
                    "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": {}}},
                })
        return normalized

    def _is_response_valid(self, result: dict[str, Any], output_model: type | None) -> bool:
        """Vérifie que la réponse est exploitable."""
        choices = result.get("choices", [])
        if not choices:
            return False
        message = choices[0].get("message", {})
        content = message.get("content")
        tool_calls = message.get("tool_calls")
        # Au moins un contenu ou des tool calls
        return bool(content) or bool(tool_calls)

    def _parse_response(self, result: dict[str, Any], output_model: type | None) -> Any:
        """Parse la réponse en format attendu par les agents."""
        choices = result.get("choices", [])
        if not choices:
            return None

        message = choices[0].get("message", {})
        content = message.get("content", "")
        message.get("tool_calls")

        # Extraire le reasoning si présent (Qwen3 thinking)
        if "reasoning_content" in message:
            message["reasoning_content"]

        # Si output_model est demandé, parser le JSON
        if output_model and content:
            try:
                parsed = json.loads(content)
                return output_model(**parsed) if hasattr(output_model, "__init__") else parsed
            except (json.JSONDecodeError, TypeError):
                pass

        # Retourner le contenu brut
        return content

    def routing_stats(self) -> dict[str, Any]:
        """Statistiques du routeur pour l'observabilité."""
        return {
            "mode": "local-llama-cpp",
            "server": self._server.base_url,
            "current_model": self._server.current_model.id if self._server.current_model else None,
            "cascade": self._cascade.stats(),
        }

    async def close(self) -> None:
        """Nettoyage complet."""
        if self._client:
            await self._client.close()
            self._client = None
        await self._server.close()


# ── API publique (compatibilité avec l'ancien llm.py) ────────────────────


def build_llm(
    provider_ids: list[str] | None = None,
    fake: bool = False,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> LLMClient:
    """Construit un client LLM local.

    - ``fake``: ignoré (compatibilité avec l'ancienne API).
    - ``provider_ids``: ignoré (compatibilité).
    - ``host/port``: serveur llama-cpp-python local.
    """
    global _client
    if _client is None:
        _client = LLMClient(host=host, port=port)
    return _client


def get_router(provider_ids: list[str] | None = None) -> LLMClient:
    """Alias pour build_llm (compatibilité)."""
    return build_llm(provider_ids=provider_ids)


def reset_router() -> None:
    """Réinitialise le singleton (tests)."""
    global _client
    _client = None


def model_name_of(result: Any) -> str:
    """Extrait le nom du modèle utilisé depuis un résultat LLM."""
    if isinstance(result, dict):
        model = result.get("model", "")
        if model:
            return str(model)
    return "local-llama-cpp"


def routing_stats() -> dict[str, Any]:
    """Statistiques du routeur partagé."""
    if _client is None:
        return {"mode": "uninitialized"}
    return _client.routing_stats()


def last_decision() -> dict[str, str]:
    """Dernier modèle réellement utilisé (compatibilité avec l'ancienne API)."""
    if _client is None:
        return {}
    model = _client._server.current_model
    if model:
        return {"provider": "local", "model": model.id}
    return {}


def last_attempt() -> dict[str, str]:
    """Dernière tentative (compatibilité avec l'ancienne API)."""
    if _client is None:
        return {}
    stats = _client.routing_stats()
    cascade = stats.get("cascade", {})
    by_model = cascade.get("by_model", {})
    if by_model:
        last_model = list(by_model.keys())[-1]
        return {"provider": "local", "model": last_model, "error": ""}
    return {}
