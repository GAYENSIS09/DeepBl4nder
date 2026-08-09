"""DeepBlender : orchestration d'agents IA (NOOA) pour la production audiovisuelle Blender."""

from __future__ import annotations

import sys

from dotenv import find_dotenv, load_dotenv

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
        setattr(fcntl, "LOCK_SH", 1)
        setattr(fcntl, "LOCK_EX", 2)
        setattr(fcntl, "LOCK_NB", 4)
        setattr(fcntl, "LOCK_UN", 8)

        def _flock(_fd: int, _operation: int) -> None:
            return None

        setattr(fcntl, "flock", _flock)
        sys.modules["fcntl"] = fcntl

    for _name, _num in (("SIGUSR1", 10), ("SIGUSR2", 12)):
        if not hasattr(signal, _name):
            setattr(signal, _name, _num)


_install_windows_shims()
