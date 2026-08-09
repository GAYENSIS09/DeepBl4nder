"""API DeepBlender : gateway HTTP minimale."""

from __future__ import annotations

from deepblender.api.server import DeepBlenderHandler, create_server, serve

__all__ = ["DeepBlenderHandler", "create_server", "serve"]
