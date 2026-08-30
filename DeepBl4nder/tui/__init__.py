"""TUI package for DeepBl4nder."""

import warnings

# Les stratégies NOOA « expérimentales » utilisées par les agents (Reflexion,
# CodeActLite, ...) émettent un FutureWarning bruyant au chargement. On filtre
# avant d'importer l'application pour garder le terminal propre.
warnings.filterwarnings(
    "ignore",
    message=r".*experimental and not actively maintained.*",
    category=FutureWarning,
)

from DeepBl4nder.tui.app import DeepBl4nderTUI  # noqa: E402

__all__ = ["DeepBl4nderTUI"]