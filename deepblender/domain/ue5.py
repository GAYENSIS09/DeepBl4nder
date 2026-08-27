"""Domaine UE5 : types pour les commandes et résultats Unreal Engine 5."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UE5Command:
    """Une commande REST à envoyer au serveur UE5."""

    endpoint: str  # ex: "level/create", "material/create"
    payload: dict[str, Any] = field(default_factory=dict)
    timeout: float = 60.0  # timeout spécifique (defaut 60s)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "payload": self.payload,
            "timeout": self.timeout,
        }


@dataclass
class UE5Commands:
    """Séquence de commandes REST pour créer une scène dans UE5.

    Généré par UE5Agent à partir d'une SceneSpec.
    """

    scene_name: str  # nom de la scène
    commands: list[UE5Command] = field(default_factory=list)
    version: int = 1

    def to_mapping(self) -> dict[str, Any]:
        return {
            "scene_name": self.scene_name,
            "commands": [c.to_mapping() for c in self.commands],
            "version": self.version,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "UE5Commands":
        commands = [
            UE5Command(
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
