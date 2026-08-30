"""Client HTTP pour le serveur local llama-cpp-python.

Interface compatible OpenAI : POST /v1/chat/completions, GET /v1/models.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("DeepBl4nder.llm.client")


class LocalLLMClient:
    """Client pour le serveur local llama-cpp-python."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080/v1"):
        self._base_url = base_url.rstrip("/")
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        """Client HTTP lazy."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=120.0)
        return self._http

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Appel POST /v1/chat/completions."""
        http = await self._get_http()

        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        if stop:
            payload["stop"] = stop

        if response_format:
            payload["response_format"] = response_format

        # Paramètres additionnels supportés par llama-cpp-python
        for key in ("top_p", "top_k", "repeat_penalty", "seed"):
            if key in kwargs:
                payload[key] = kwargs[key]

        logger.debug(
            "Appel chat_completion : %d messages, max_tokens=%d",
            len(messages), max_tokens,
        )

        try:
            resp = await http.post(f"{self._base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Erreur HTTP %d : %s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise
        except httpx.ConnectError:
            raise ConnectionError(
                f"Impossible de se connecter au serveur LLM sur {self._base_url}. "
                "Vérifiez que le serveur est démarré."
            )

    async def list_models(self) -> list[dict[str, Any]]:
        """GET /v1/models — liste les modèles chargés."""
        http = await self._get_http()
        resp = await http.get(f"{self._base_url}/models")
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    async def health(self) -> bool:
        """Vérifie la santé du serveur."""
        try:
            http = await self._get_http()
            resp = await http.get(f"{self._base_url}/models")
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    async def close(self) -> None:
        """Ferme le client HTTP."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None
