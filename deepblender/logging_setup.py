"""Journalisation complète de l'arrière-plan DeepBl4nder.

Un seul appel à ``setup_logging()`` configure :

- la console (stdout) ;
- un fichier rotatif ``$DeepBl4nder_DATA_DIR/logs/DeepBl4nder.log``
  (5 Mo × 5 fichiers) qui conserve TOUT ce qui se passe en arrière-plan :
  étapes du pipeline, appels/votes/échecs LLM, découvertes de modèles…

Variables d'environnement :

- ``DeepBl4nder_LOG_LEVEL`` : niveau global (INFO par défaut ; DEBUG =
  journalisation exhaustive des décisions internes) ;
- ``DeepBl4nder_DATA_DIR`` : racine des données (logs sous-dossier ``logs``).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"

# Loggers tiers bruyants : silenciés sauf en DEBUG explicite.
_THIRD_PARTY_LOGGERS = ("litellm", "httpx", "httpcore", "openai")


def log_file_path(data_dir: str | None = None) -> Path:
    """Chemin du fichier de journal rotatif."""
    base = data_dir or os.environ.get("DeepBl4nder_DATA_DIR", "data")
    return Path(base) / "logs" / "DeepBl4nder.log"


def setup_logging(level: str | None = None, data_dir: str | None = None) -> Path:
    """Attache console + fichier rotatif au logger racine ``DeepBl4nder``.

    Idempotent : peut être appelé depuis l'API, le CLI ou les runners sans
    dupliquer les handlers. Retourne le chemin du fichier de journal.
    """
    resolved = (level or os.environ.get("DeepBl4nder_LOG_LEVEL", "INFO")).upper()
    lvl = getattr(logging, resolved, logging.INFO)

    root = logging.getLogger("DeepBl4nder")
    root.setLevel(lvl)
    root.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    has_console = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in root.handlers
    )
    if not has_console:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        console.setLevel(lvl)
        root.addHandler(console)

    path = log_file_path(data_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:  # noqa: PERF203 - disque plein/lecture seule : console seule
        path = None  # type: ignore[assignment]
    if path is not None:
        target = str(path.resolve())
        has_file = any(
            isinstance(h, logging.handlers.RotatingFileHandler)
            and getattr(h, "baseFilename", None) == target
            for h in root.handlers
        )
        if not has_file:
            file_handler = logging.handlers.RotatingFileHandler(
                target,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)  # le fichier garde tout
            root.addHandler(file_handler)

    for name in _THIRD_PARTY_LOGGERS:
        logging.getLogger(name).setLevel(logging.DEBUG if lvl <= logging.DEBUG else logging.WARNING)

    return path if path is not None else log_file_path(data_dir)
