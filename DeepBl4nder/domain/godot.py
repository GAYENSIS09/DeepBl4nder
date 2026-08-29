"""Domaine Godot : types pour les commandes et résultats Godot 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GodotCommand:
    """Une commande REST à envoyer au serveur Godot."""

    endpoint: str  # ex: "scene/create", "mesh/create"
    payload: dict[str, Any] = field(default_factory=dict)
    timeout: float = 60.0

    def to_mapping(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "payload": self.payload,
            "timeout": self.timeout,
        }


@dataclass
class GodotCommands:
    """Séquence de commandes REST pour créer une scène dans Godot."""

    scene_name: str
    commands: list[GodotCommand] = field(default_factory=list)
    version: int = 1

    def to_mapping(self) -> dict[str, Any]:
        return {
            "scene_name": self.scene_name,
            "commands": [c.to_mapping() for c in self.commands],
            "version": self.version,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "GodotCommands":
        commands = [
            GodotCommand(
                endpoint=c["endpoint"],
                payload=c.get("payload", {}),
                timeout=c.get("timeout", 60.0),
            )
            for c in data.get("commands", [])
        ]
        return cls(
            scene_name=data.get("scene_name", ""),
            commands=commands,
            version=data.get("version", 1),
        )
