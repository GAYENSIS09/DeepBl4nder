"""Journalisation arrière-plan : console + fichier rotatif."""

from __future__ import annotations

import logging
import logging.handlers

from DeepBl4nder.logging_setup import log_file_path, setup_logging


def test_setup_logging_writes_background_events_to_file(tmp_path) -> None:
    data_dir = tmp_path / "data"
    path = setup_logging(data_dir=str(data_dir))
    assert path == log_file_path(str(data_dir))

    root = logging.getLogger("DeepBl4nder")
    file_handlers = [
        h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert any(h.baseFilename == str(path.resolve()) for h in file_handlers)

    logging.getLogger("DeepBl4nder.test").info("événement de contrôle %s", 42)
    for handler in root.handlers:
        handler.flush()
    content = path.read_text(encoding="utf-8")
    assert "événement de contrôle 42" in content
    assert "DeepBl4nder.test" in content

    # Nettoyage : détacher les handlers pointant vers le répertoire temporaire.
    for handler in list(root.handlers):
        basefile = getattr(handler, "baseFilename", "")
        if str(tmp_path) in basefile:
            root.removeHandler(handler)
            handler.close()


def test_setup_logging_is_idempotent(tmp_path) -> None:
    data_dir = tmp_path / "data"
    setup_logging(data_dir=str(data_dir))
    before = len(logging.getLogger("DeepBl4nder").handlers)
    setup_logging(data_dir=str(data_dir))
    after = len(logging.getLogger("DeepBl4nder").handlers)
    assert before == after
