"""Gestionnaire de serveur llama-cpp-python en arrière-plan.

Lance et gère un serveur HTTP compatible OpenAI pour les modèles GGUF.
Le serveur utilise l'API intégrée de llama-cpp-python.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Any

import httpx

from DeepBl4nder.llm.model_registry import LocalModel

logger = logging.getLogger("DeepBl4nder.llm.server")

# Configuration par défaut
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
STARTUP_TIMEOUT_S = 60.0
HEALTH_CHECK_INTERVAL_S = 2.0


class ModelServer:
    """Gère le serveur llama-cpp-python en arrière-plan."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ):
        self._host = host
        self._port = port
        self._process: subprocess.Popen | None = None
        self._current_model: LocalModel | None = None
        self._http: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        """URL de base du serveur (format OpenAI)."""
        return f"http://{self._host}:{self._port}/v1"

    @property
    def is_running(self) -> bool:
        """True si le serveur tourne."""
        return self._process is not None and self._process.poll() is None

    @property
    def current_model(self) -> LocalModel | None:
        """Modèle actuellement chargé."""
        return self._current_model

    async def _get_http(self) -> httpx.AsyncClient:
        """Client HTTP lazy."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=120.0)
        return self._http

    async def start(self, model: LocalModel) -> None:
        """Démarre le serveur avec un modèle donné."""
        if self.is_running and self._current_model and self._current_model.id == model.id:
            logger.debug("Serveur déjà en cours avec le modèle %s", model.id)
            return

        if self.is_running:
            await self.stop()

        if not model.gguf_path.exists():
            raise FileNotFoundError(
                f"Fichier GGUF introuvable : {model.gguf_path}\n"
                f"Exécutez : python -m DeepBl4nder.llm.download"
            )

        logger.info("Démarrage du serveur avec le modèle %s (%s)", model.id, model.gguf_path)

        cmd = [
            sys.executable, "-m", "llama_cpp.server",
            "--model", str(model.gguf_path),
            "--host", self._host,
            "--port", str(self._port),
            "--n_ctx", str(model.context_window),
            "--n_gpu_layers", "-1",  # Auto: tout ce qui rentre en VRAM
            "--chat_format", "chatml",  # Format compatible Qwen
        ]

        # Options supplémentaires depuis l'environnement
        extra_layers = os.getenv("DeepBl4nder_N_GPU_LAYERS")
        if extra_layers:
            cmd[cmd.index("--n_gpu_layers") + 1] = extra_layers

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if not os.getenv("DeepBl4nder_SERVER_VERBOSE") else None,
                stderr=subprocess.PIPE if not os.getenv("DeepBl4nder_SERVER_VERBOSE") else None,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "llama-cpp-python non installé. "
                "Installez-le avec : pip install 'DeepBl4nder[local-llm]'"
            ) from exc

        self._current_model = model

        # Attendre que le serveur soit prêt
        await self._wait_for_ready()
        logger.info("Serveur prêt sur %s (modèle %s)", self.base_url, model.id)

    async def stop(self) -> None:
        """Arrête le serveur proprement."""
        if self._process is None:
            return

        logger.info("Arrêt du serveur...")
        try:
            if sys.platform == "win32":
                self._process.terminate()
            else:
                self._process.send_signal(signal.SIGTERM)
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Erreur lors de l'arrêt du serveur : %s", exc)
        finally:
            self._process = None
            self._current_model = None
            logger.info("Serveur arrêté")

    async def ensure_model(self, model: LocalModel) -> None:
        """S'assure que le modèle est chargé, change si nécessaire."""
        if self._current_model and self._current_model.id == model.id and self.is_running:
            return
        await self.start(model)

    async def switch_model(self, model: LocalModel) -> None:
        """Change de modèle (redémarre le serveur si nécessaire)."""
        await self.start(model)

    async def _wait_for_ready(self) -> None:
        """Attend que le serveur soit prêt à recevoir des requêtes."""
        http = await self._get_http()
        start = time.monotonic()

        while time.monotonic() - start < STARTUP_TIMEOUT_S:
            if not self.is_running:
                raise RuntimeError("Le serveur s'est arrêté prématurément")
            try:
                resp = await http.get(f"{self.base_url}/models")
                if resp.status_code == 200:
                    return
            except (httpx.ConnectError, httpx.ReadTimeout):
                pass
            await asyncio.sleep(HEALTH_CHECK_INTERVAL_S)

        raise TimeoutError(
            f"Le serveur n'a pas démarré en {STARTUP_TIMEOUT_S}s"
        )

    async def health_check(self) -> bool:
        """Vérifie que le serveur est opérationnel."""
        if not self.is_running:
            return False
        try:
            http = await self._get_http()
            resp = await http.get(f"{self.base_url}/models")
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    async def get_model_info(self) -> dict[str, Any]:
        """Retourne les infos du modèle chargé."""
        try:
            http = await self._get_http()
            resp = await http.get(f"{self.base_url}/models")
            if resp.status_code == 200:
                return resp.json()
        except Exception:  # noqa: BLE001
            pass
        return {"data": []}

    async def close(self) -> None:
        """Nettoyage complet."""
        await self.stop()
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None
