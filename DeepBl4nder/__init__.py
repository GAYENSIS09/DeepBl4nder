"""DeepBl4nder : orchestration d'agents IA (NOOA) pour la production audiovisuelle Blender."""

from __future__ import annotations

import sys
import warnings

from dotenv import find_dotenv, load_dotenv

# Les stratégies NOOA « expérimentales » utilisées par les agents (Reflexion,
# CodeActLite, ...) émettent un FutureWarning bruyant au chargement des modules
# (décorateurs `@strategy(...)` au niveau classe). On les filtre dès le premier
# import du paquet pour garder le terminal de l'application propre.
warnings.filterwarnings(
    "ignore",
    message=r".*experimental and not actively maintained.*",
    category=FutureWarning,
)

load_dotenv(find_dotenv())

__version__ = "0.2.0"


def _install_windows_shims() -> None:
    """NOOA 0.0.x imports ``fcntl`` and ``signal.SIGUSR2`` unconditionally (Unix-only).

    Mirrored in ``sitecustomize.py`` for interpreters that never import this
    package; the in-package fallback covers clean installs (wheel/venv/Docker).
    """
    if sys.platform != "win32":
        return
    import signal
    import types

    if "fcntl" not in sys.modules:
        fcntl = types.ModuleType("fcntl")
        fcntl.LOCK_SH = 1
        fcntl.LOCK_EX = 2
        fcntl.LOCK_NB = 4
        fcntl.LOCK_UN = 8

        def _flock(_fd: int, _operation: int) -> None:
            return None

        fcntl.flock = _flock
        sys.modules["fcntl"] = fcntl

    for _name, _num in (("SIGUSR1", 10), ("SIGUSR2", 12)):
        if not hasattr(signal, _name):
            setattr(signal, _name, _num)


def _install_utf8_stdio() -> None:
    """Force un stdout/stderr UTF-8 (erreurs non bloquantes).

    Sous Windows la console par défaut est cp1252 : un ``print`` contenant des
    caractères non-ASCII (ex. le glyphe ⚠ des bascules LLM) lève
    ``UnicodeEncodeError`` et peut faire échouer un run au milieu du failover.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


_install_windows_shims()
_install_utf8_stdio()
