"""UE5Bridge : client REST pour Unreal Engine 5.

Communique avec un serveur UE5 (Python plugin) via HTTP REST.
Le serveur UE5 doit tourner sur le port configuré (defaut : 8080).

Architecture :
  DeepBl4nder → UE5Bridge → REST API → UE5 Server (Python plugin)
                                           ├── Level creation
                                           ├── Material setup (Lumen)
                                           ├── Lighting (Lumen GI)
                                           ├── Sequencer (animation)
                                           └── MRQ (Movie Render Queue)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger("DeepBl4nder.bridges.ue5")


class UE5ConnectionError(RuntimeError):
    """Le serveur UE5 n'est pas accessible."""


class UE5CommandError(RuntimeError):
    """Une commande UE5 a échoué."""


@dataclass
class UE5CommandResult:
    """Résultat d'une commande UE5."""

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


class UE5Bridge:
    """Client REST pour communiquer avec un serveur UE5.

    Le serveur UE5 doit exposer une API REST avec les endpoints :
    - GET  /health               → status du serveur
    - POST /level/create         → crée un niveau
    - POST /asset/import         → importe un asset
    - POST /material/create      → crée un matériau Lumen
    - POST /lighting/setup       → configure l'éclairage
    - POST /sequencer/setup      → configure l'animation
    - POST /render/start         → lance le rendu MRQ
    - POST /render/status        → vérifie le statut du rendu
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 60.0,
        render_timeout: float = 600.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._render_timeout = render_timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "DeepBl4nder-UE5/0.3",
        })

    def available(self) -> bool:
        """Vérifie si le serveur UE5 est accessible."""
        try:
            resp = self._session.get(
                f"{self._base_url}/health",
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """Récupère le statut du serveur UE5."""
        try:
            resp = self._session.get(
                f"{self._base_url}/health",
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Level ──────────────────────────────────────────────────────

    def create_level(self, name: str, template: str = "empty") -> UE5CommandResult:
        """Crée un niveau dans UE5."""
        return self._command("level/create", {
            "name": name,
            "template": template,
        })

    def delete_level(self, name: str) -> UE5CommandResult:
        """Supprime un niveau."""
        return self._command("level/delete", {"name": name})

    # ── Assets ─────────────────────────────────────────────────────

    def import_asset(
        self,
        source_path: str,
        destination: str,
        asset_type: str = "auto",
    ) -> UE5CommandResult:
        """Importe un asset (.fbx, .gltf, .glb, .uasset) dans UE5."""
        return self._command("asset/import", {
            "source": source_path,
            "destination": destination,
            "type": asset_type,
        })

    def create_actor(
        self,
        actor_type: str,
        name: str,
        transform: dict[str, Any] | None = None,
        asset_path: str = "",
    ) -> UE5CommandResult:
        """Crée un acteur dans le niveau courant."""
        payload: dict[str, Any] = {
            "type": actor_type,
            "name": name,
        }
        if transform:
            payload["transform"] = transform
        if asset_path:
            payload["asset"] = asset_path
        return self._command("actor/create", payload)

    # ── Materials ──────────────────────────────────────────────────

    def create_material(
        self,
        name: str,
        base_color: tuple[float, float, float] = (0.8, 0.8, 0.8),
        metallic: float = 0.0,
        roughness: float = 0.5,
        emission_color: tuple[float, float, float] | None = None,
        emission_intensity: float = 0.0,
        texture_path: str = "",
    ) -> UE5CommandResult:
        """Crée un matériau PBR Lumen dans UE5."""
        properties: dict[str, Any] = {
            "base_color": list(base_color),
            "metallic": metallic,
            "roughness": roughness,
        }
        if emission_color is not None:
            properties["emission_color"] = list(emission_color)
            properties["emission_intensity"] = emission_intensity
        if texture_path:
            properties["texture"] = texture_path
        return self._command("material/create", {
            "name": name,
            **properties,
        })

    def apply_material(self, actor_name: str, material_name: str) -> UE5CommandResult:
        """Applique un matériau à un acteur."""
        return self._command("material/apply", {
            "actor": actor_name,
            "material": material_name,
        })

    # ── Lighting ───────────────────────────────────────────────────

    def setup_lighting(
        self,
        lights: list[dict[str, Any]],
        use_lumen: bool = True,
        skylight_intensity: float = 1.0,
        environment_color: tuple[float, float, float] = (0.1, 0.1, 0.15),
    ) -> UE5CommandResult:
        """Configure l'éclairage Lumen."""
        return self._command("lighting/setup", {
            "lights": lights,
            "use_lumen": use_lumen,
            "skylight_intensity": skylight_intensity,
            "environment_color": list(environment_color),
        })

    def create_light(
        self,
        light_type: str,
        name: str,
        location: tuple[float, float, float] = (0, 0, 300),
        intensity: float = 10.0,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
        attenuation_radius: float = 1000.0,
    ) -> UE5CommandResult:
        """Crée une lumière individuelle."""
        return self._command("light/create", {
            "type": light_type,
            "name": name,
            "location": list(location),
            "intensity": intensity,
            "color": list(color),
            "attenuation_radius": attenuation_radius,
        })

    # ── Sequencer (Animation) ──────────────────────────────────────

    def setup_sequencer(
        self,
        sequence_name: str,
        duration_frames: int = 240,
        fps: int = 24,
        tracks: list[dict[str, Any]] | None = None,
    ) -> UE5CommandResult:
        """Configure le Sequencer pour l'animation."""
        return self._command("sequencer/setup", {
            "name": sequence_name,
            "duration_frames": duration_frames,
            "fps": fps,
            "tracks": tracks or [],
        })

    def add_camera_track(
        self,
        sequence_name: str,
        camera_name: str,
        keyframes: list[dict[str, Any]],
    ) -> UE5CommandResult:
        """Ajoute un track caméra au Sequencer."""
        return self._command("sequencer/add_camera", {
            "sequence": sequence_name,
            "camera": camera_name,
            "keyframes": keyframes,
        })

    def add_actor_track(
        self,
        sequence_name: str,
        actor_name: str,
        property_path: str,
        keyframes: list[dict[str, Any]],
    ) -> UE5CommandResult:
        """Ajoute un track d'animation d'acteur au Sequencer."""
        return self._command("sequencer/add_actor_track", {
            "sequence": sequence_name,
            "actor": actor_name,
            "property": property_path,
            "keyframes": keyframes,
        })

    # ── Render (MRQ) ───────────────────────────────────────────────

    def start_render(
        self,
        output_path: str,
        sequence_name: str = "",
        resolution: tuple[int, int] = (1920, 1080),
        format: str = "mp4",
        quality: str = "cinematic",
        anti_aliasing: int = 1,
        override_existing: bool = True,
    ) -> UE5CommandResult:
        """Lance le rendu via MRQ (Movie Render Queue)."""
        return self._command("render/start", {
            "output": output_path,
            "sequence": sequence_name,
            "resolution": list(resolution),
            "format": format,
            "quality": quality,
            "anti_aliasing": anti_aliasing,
            "override_existing": override_existing,
        }, timeout=self._render_timeout)

    def get_render_status(self) -> UE5CommandResult:
        """Vérifie le statut du rendu en cours."""
        return self._command("render/status", {})

    def cancel_render(self) -> UE5CommandResult:
        """Annule le rendu en cours."""
        return self._command("render/cancel", {})

    # ── Console Variables ──────────────────────────────────────────

    def set_cvar(self, name: str, value: float | int | str) -> UE5CommandResult:
        """Définit une console variable UE5."""
        return self._command("cvar/set", {"name": name, "value": value})

    def set_quality_preset(self, preset: str) -> UE5CommandResult:
        """Définit le preset de qualité (low, medium, high, epic, cinematic)."""
        return self._command("quality/preset", {"preset": preset})

    # ── Internal ───────────────────────────────────────────────────

    def _command(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout: float | None = None,
    ) -> UE5CommandResult:
        """Exécute une commande REST vers le serveur UE5."""
        url = f"{self._base_url}/{endpoint}"
        timeout = timeout or self._timeout

        try:
            resp = self._session.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("UE5 command OK: %s → %s", endpoint, data.get("status", "ok"))
            return UE5CommandResult(ok=True, endpoint=endpoint, data=data)
        except requests.ConnectionError as e:
            msg = f"UE5 server not reachable at {self._base_url}: {e}"
            logger.error(msg)
            raise UE5ConnectionError(msg) from e
        except requests.HTTPError as e:
            error_body = ""
            if e.response is not None:
                try:
                    error_body = e.response.text[:500]
                except Exception:
                    pass
            msg = f"UE5 command failed: {endpoint} → {e.response.status_code}: {error_body}"
            logger.error(msg)
            return UE5CommandResult(ok=False, endpoint=endpoint, error=msg)
        except Exception as e:
            msg = f"UE5 command error: {endpoint} → {e}"
            logger.error(msg)
            return UE5CommandResult(ok=False, endpoint=endpoint, error=msg)
