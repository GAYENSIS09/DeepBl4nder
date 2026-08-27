"""CLI : commandes inspect, validate et --version."""

from __future__ import annotations

from pathlib import Path

import pytest

from DeepBl4nder import __version__
from DeepBl4nder.cli import main


def test_version_flag() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_inspect_returns_zero(capsys) -> None:  # noqa: ANN001
    assert main(["inspect"]) == 0
    output = capsys.readouterr().out
    assert __version__ in output
    assert "NOOA" in output


def test_validate_ok(tmp_path) -> None:  # noqa: ANN001
    script = tmp_path / "safe.py"
    script.write_text("import bpy\nprint('ok')\n", encoding="utf-8")
    assert main(["validate", str(script)]) == 0


def test_validate_rejected(tmp_path, capsys) -> None:  # noqa: ANN001
    script = tmp_path / "bad.py"
    script.write_text("import os\nos.system('ls')\n", encoding="utf-8")
    assert main(["validate", str(script)]) == 1
    assert "refusé" in capsys.readouterr().err


def test_validate_missing_file() -> None:
    assert main(["validate", str(Path("does-not-exist.py"))]) == 2
