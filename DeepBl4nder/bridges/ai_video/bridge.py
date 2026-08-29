"""AIVideoBridge : client REST pour la génération vidéo par IA.

Communique avec un serveur AI Video (REST API) via HTTP.
Le serveur doit tourner sur le port configuré (defaut : 8082).

Architecture :
  DeepBl4nder → AIVideoBridge → REST API → AI Video Server (GPU)
                                            ├── Text-to-Video (CogVideoX, Wan2.1, AnimateDiff)
                                            ├── Image-to-Video (SVD)
                                            ├── Cache management
                                            └── GPU inference
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger("DeepBl4nder.bridges.ai_video")


class AIVideoConnectionError(RuntimeError):
    """Le serveur AI Video n'est pas accessible."""


class AIVideoCommandError(RuntimeError):
    """Une commande AI Video a échoué."""


@dataclass
class AIVideoCommandResult:
    """Résultat d'une commande AI Video."""

    ok: bool
    endpoint: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_mapping(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "endpoint": self.endpoint,
            "data": self.data,
            "error": self.error,
        }


class AIVideoBridge:
    """Client REST pour communiquer avec un serveur AI Video.

    Le serveur AI Video doit exposer une API REST avec les endpoints :
    - GET  /health                → status du serveur
    - POST /generate/t2v          → text-to-video generation
    - POST /generate/i2v          → image-to-video generation
    - GET  /generate/status       → status de la génération
    - POST /generate/cancel       → annuler la génération
    - GET  /cache/stats           → statistiques du cache
    - POST /cache/clear           → vider le cache
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8082",
        timeout: float = 60.0,
        generation_timeout: float = 600.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._generation_timeout = generation_timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "DeepBl4nder-AIVideo/0.1",
        })

    def available(self) -> bool:
        """Vérifie si le serveur AI Video est accessible."""
        try:
            resp = self._session.get(f"{self._base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """Récupère le statut du serveur AI Video."""
        try:
            resp = self._session.get(f"{self._base_url}/health", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Text-to-Video ────────────────────────────────────────────

    def generate_text_to_video(
        self,
        prompt: str,
        model: str = "cogvideox",
        seed: int = 42,
        num_frames: int = 49,
        width: int = 1024,
        height: int = 576,
        guidance_scale: float = 6.0,
        num_inference_steps: int = 50,
        use_cache: bool = True,
    ) -> AIVideoCommandResult:
        """Génère une vidéo à partir d'un prompt textuel."""
        return self._command("generate/t2v", {
            "prompt": prompt,
            "model": model,
            "seed": seed,
            "num_frames": num_frames,
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "use_cache": use_cache,
        }, timeout=self._generation_timeout)

    # ── Image-to-Video ───────────────────────────────────────────

    def generate_image_to_video(
        self,
        image_path: str,
        model: str = "svd",
        prompt: str = "",
        seed: int = 42,
        num_frames: int = 25,
        motion_bucket_id: int = 127,
        width: int = 1024,
        height: int = 576,
        use_cache: bool = True,
    ) -> AIVideoCommandResult:
        """Génère une vidéo à partir d'une image."""
        return self._command("generate/i2v", {
            "image_path": image_path,
            "model": model,
            "prompt": prompt,
            "seed": seed,
            "num_frames": num_frames,
            "motion_bucket_id": motion_bucket_id,
            "width": width,
            "height": height,
            "use_cache": use_cache,
        }, timeout=self._generation_timeout)

    # ── Status ───────────────────────────────────────────────────

    def get_generation_status(self) -> AIVideoCommandResult:
        """Vérifie le statut de la génération en cours."""
        return self._command("generate/status", {})

    def cancel_generation(self) -> AIVideoCommandResult:
        """Annule la génération en cours."""
        return self._command("generate/cancel", {})

    # ── Cache ────────────────────────────────────────────────────

    def get_cache_stats(self) -> AIVideoCommandResult:
        """Récupère les statistiques du cache."""
        return self._command("cache/stats", {})

    def clear_cache(self) -> AIVideoCommandResult:
        """Vide le cache des générations."""
        return self._command("cache/clear", {})

    # ── Internal ─────────────────────────────────────────────────

    def _command(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout: float | None = None,
    ) -> AIVideoCommandResult:
        """Exécute une commande REST vers le serveur AI Video."""
        url = f"{self._base_url}/{endpoint}"
        timeout = timeout or self._timeout

        try:
            resp = self._session.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("AI Video command OK: %s → %s", endpoint, data.get("status", "ok"))
            return AIVideoCommandResult(ok=True, endpoint=endpoint, data=data)
        except requests.ConnectionError as e:
            msg = f"AI Video server not reachable at {self._base_url}: {e}"
            logger.error(msg)
            raise AIVideoConnectionError(msg) from e
        except requests.HTTPError as e:
            error_body = ""
            if e.response is not None:
                try:
                    error_body = e.response.text[:500]
                except Exception:
                    pass
            msg = f"AI Video command failed: {endpoint} → {e.response.status_code}: {error_body}"
            logger.error(msg)
            return AIVideoCommandResult(ok=False, endpoint=endpoint, error=msg)
        except Exception as e:
            msg = f"AI Video command error: {endpoint} → {e}"
            logger.error(msg)
            return AIVideoCommandResult(ok=False, endpoint=endpoint, error=msg)
