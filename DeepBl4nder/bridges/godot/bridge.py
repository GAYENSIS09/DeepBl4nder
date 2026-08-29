"""GodotBridge : client REST pour Godot 4.

Communique avec un serveur Godot (REST API) via HTTP.
Le serveur Godot doit tourner sur le port configuré (defaut : 8081).

Architecture :
  DeepBl4nder → GodotBridge → REST API → Godot Server (headless)
                                         ├── Scene creation
                                         ├── Mesh creation
                                         ├── PBR materials
                                         ├── Lighting
                                         ├── Animation
                                         └── Render / Export
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger("DeepBl4nder.bridges.godot")


class GodotConnectionError(RuntimeError):
    """Le serveur Godot n'est pas accessible."""


class GodotCommandError(RuntimeError):
    """Une commande Godot a échoué."""


@dataclass
class GodotCommandResult:
    """Résultat d'une commande Godot."""

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


class GodotBridge:
    """Client REST pour communiquer avec un serveur Godot.

    Le serveur Godot doit exposer une API REST avec les endpoints :
    - GET  /health              → status du serveur
    - POST /scene/create        → crée une scène
    - POST /mesh/create         → crée un mesh
    - POST /material/create     → crée un matériau PBR
    - POST /material/apply      → applique un matériau
    - POST /camera/create       → crée une caméra
    - POST /light/create        → crée une lumière
    - POST /lighting/setup      → configure l'éclairage
    - POST /animation/track     → ajoute une piste d'animation
    - POST /render/start        → lance le rendu
    - POST /export              → exporte le projet (WebGL, desktop)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        timeout: float = 60.0,
        render_timeout: float = 600.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._render_timeout = render_timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "DeepBl4nder-Godot/0.1",
        })

    def available(self) -> bool:
        """Vérifie si le serveur Godot est accessible."""
        try:
            resp = self._session.get(f"{self._base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """Récupère le statut du serveur Godot."""
        try:
            resp = self._session.get(f"{self._base_url}/health", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Scene ────────────────────────────────────────────────────

    def create_scene(self, name: str, description: str = "") -> GodotCommandResult:
        """Crée une scène dans Godot."""
        return self._command("scene/create", {"name": name, "description": description})

    def delete_scene(self, name: str) -> GodotCommandResult:
        """Supprime une scène."""
        return self._command("scene/delete", {"name": name})

    # ── Mesh ─────────────────────────────────────────────────────

    def create_mesh(
        self,
        name: str,
        mesh_type: str = "cube",
        size: tuple[float, float, float] = (1.0, 1.0, 1.0),
        position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> GodotCommandResult:
        """Crée un mesh dans la scène."""
        return self._command("mesh/create", {
            "name": name,
            "type": mesh_type,
            "size": list(size),
            "position": list(position),
        })

    # ── Material ─────────────────────────────────────────────────

    def create_material(
        self,
        name: str,
        base_color: tuple[float, float, float] = (0.8, 0.8, 0.8),
        metallic: float = 0.0,
        roughness: float = 0.5,
        emission_color: tuple[float, float, float] | None = None,
        emission_energy: float = 0.0,
    ) -> GodotCommandResult:
        """Crée un matériau PBR dans Godot."""
        properties: dict[str, Any] = {
            "name": name,
            "base_color": list(base_color),
            "metallic": metallic,
            "roughness": roughness,
        }
        if emission_color is not None:
            properties["emission_color"] = list(emission_color)
            properties["emission_energy"] = emission_energy
        return self._command("material/create", properties)

    def apply_material(self, mesh_name: str, material_name: str) -> GodotCommandResult:
        """Applique un matériau à un mesh."""
        return self._command("material/apply", {"mesh": mesh_name, "material": material_name})

    # ── Camera ───────────────────────────────────────────────────

    def create_camera(
        self,
        name: str,
        position: tuple[float, float, float] = (0.0, 3.0, 8.0),
        look_at: tuple[float, float, float] = (0.0, 1.0, 0.0),
        fov: float = 75.0,
    ) -> GodotCommandResult:
        """Crée une caméra dans la scène."""
        return self._command("camera/create", {
            "name": name,
            "position": list(position),
            "look_at": list(look_at),
            "fov": fov,
        })

    # ── Lighting ─────────────────────────────────────────────────

    def create_light(
        self,
        light_type: str,
        name: str,
        position: tuple[float, float, float] = (0.0, 3.0, 0.0),
        rotation: tuple[float, float, float] = (-45.0, 0.0, 0.0),
        energy: float = 2.0,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> GodotCommandResult:
        """Crée une lumière."""
        return self._command("light/create", {
            "type": light_type,
            "name": name,
            "position": list(position),
            "rotation": list(rotation),
            "energy": energy,
            "color": list(color),
        })

    def setup_lighting(
        self,
        lights: list[dict[str, Any]],
        use_glow: bool = True,
        ambient_light_energy: float = 0.3,
    ) -> GodotCommandResult:
        """Configure l'éclairage global."""
        return self._command("lighting/setup", {
            "lights": lights,
            "use_glow": use_glow,
            "ambient_light_energy": ambient_light_energy,
        })

    # ── Animation ────────────────────────────────────────────────

    def add_animation_track(
        self,
        target: str,
        keyframes: list[dict[str, Any]],
        duration: float = 2.0,
    ) -> GodotCommandResult:
        """Ajoute une piste d'animation."""
        return self._command("animation/track", {
            "target": target,
            "keyframes": keyframes,
            "duration": duration,
        })

    # ── Render ───────────────────────────────────────────────────

    def start_render(
        self,
        output_path: str,
        scene_name: str = "current_scene",
        resolution: tuple[int, int] = (1920, 1080),
        format: str = "png",
    ) -> GodotCommandResult:
        """Lance le rendu."""
        return self._command("render/start", {
            "output": output_path,
            "scene": scene_name,
            "resolution": list(resolution),
            "format": format,
        }, timeout=self._render_timeout)

    def get_render_status(self) -> GodotCommandResult:
        """Vérifie le statut du rendu."""
        return self._command("render/status", {})

    def cancel_render(self) -> GodotCommandResult:
        """Annule le rendu."""
        return self._command("render/cancel", {})

    # ── Export ───────────────────────────────────────────────────

    def export_project(
        self,
        preset: str = "web",
        output_path: str = "build/index.html",
    ) -> GodotCommandResult:
        """Exporte le projet Godot."""
        return self._command("export", {"preset": preset, "output_path": output_path})

    # ── Internal ─────────────────────────────────────────────────

    def _command(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout: float | None = None,
    ) -> GodotCommandResult:
        """Exécute une commande REST vers le serveur Godot."""
        url = f"{self._base_url}/{endpoint}"
        timeout = timeout or self._timeout

        try:
            resp = self._session.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("Godot command OK: %s → %s", endpoint, data.get("status", "ok"))
            return GodotCommandResult(ok=True, endpoint=endpoint, data=data)
        except requests.ConnectionError as e:
            msg = f"Godot server not reachable at {self._base_url}: {e}"
            logger.error(msg)
            raise GodotConnectionError(msg) from e
        except requests.HTTPError as e:
            error_body = ""
            if e.response is not None:
                try:
                    error_body = e.response.text[:500]
                except Exception:
                    pass
            msg = f"Godot command failed: {endpoint} → {e.response.status_code}: {error_body}"
            logger.error(msg)
            return GodotCommandResult(ok=False, endpoint=endpoint, error=msg)
        except Exception as e:
            msg = f"Godot command error: {endpoint} → {e}"
            logger.error(msg)
            return GodotCommandResult(ok=False, endpoint=endpoint, error=msg)
