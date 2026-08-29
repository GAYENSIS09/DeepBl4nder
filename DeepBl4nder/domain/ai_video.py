"""Domaine AI Video : types pour les commandes et résultats de génération vidéo par IA."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIVideoCommand:
    """Une commande de génération vidéo par IA."""

    endpoint: str  # ex: "generate/t2v", "generate/i2v"
    payload: dict[str, Any] = field(default_factory=dict)
    timeout: float = 300.0  # timeout plus long pour la génération GPU

    def to_mapping(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "payload": self.payload,
            "timeout": self.timeout,
        }


@dataclass
class AIVideoCommands:
    """Séquence de commandes de génération vidéo par IA."""

    scene_name: str
    commands: list[AIVideoCommand] = field(default_factory=list)
    version: int = 1

    def to_mapping(self) -> dict[str, Any]:
        return {
            "scene_name": self.scene_name,
            "commands": [c.to_mapping() for c in self.commands],
            "version": self.version,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AIVideoCommands":
        commands = [
            AIVideoCommand(
                endpoint=c["endpoint"],
                payload=c.get("payload", {}),
                timeout=c.get("timeout", 300.0),
            )
            for c in data.get("commands", [])
        ]
        return cls(
            scene_name=data.get("scene_name", ""),
            commands=commands,
            version=data.get("version", 1),
        )


@dataclass
class AIVideoRenderSpec:
    """Paramètres spécifiques à la génération vidéo par IA."""

    model: str = "cogvideox"  # cogvideox, wan2.1, animatediff, svd, ltx, mochi
    mode: str = "t2v"  # t2v (text-to-video), i2v (image-to-video)
    seed: int = 42  # seed pour la reproductibilité
    num_frames: int = 49  # nombre de frames
    guidance_scale: float = 6.0  # force du prompt
    num_inference_steps: int = 50  # étapes d'inférence
    motion_bucket_id: int = 127  # intensité du mouvement (SVD)
    use_cache: bool = True  # activer le cache des générations
    cache_ttl: int = 3600  # durée de vie du cache en secondes

    def to_mapping(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "mode": self.mode,
            "seed": self.seed,
            "num_frames": self.num_frames,
            "guidance_scale": self.guidance_scale,
            "num_inference_steps": self.num_inference_steps,
            "motion_bucket_id": self.motion_bucket_id,
            "use_cache": self.use_cache,
            "cache_ttl": self.cache_ttl,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AIVideoRenderSpec":
        return cls(
            model=data.get("model", "cogvideox"),
            mode=data.get("mode", "t2v"),
            seed=data.get("seed", 42),
            num_frames=data.get("num_frames", 49),
            guidance_scale=data.get("guidance_scale", 6.0),
            num_inference_steps=data.get("num_inference_steps", 50),
            motion_bucket_id=data.get("motion_bucket_id", 127),
            use_cache=data.get("use_cache", True),
            cache_ttl=data.get("cache_ttl", 3600),
        )
