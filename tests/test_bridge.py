"""Frontière de processus : WorkerProcess et BlenderBridge."""

from __future__ import annotations

import sys

import pytest

from deepblender.blender.bridge import BlenderBridge, BlenderNotFoundError
from deepblender.bridge.worker import WorkerCommand, WorkerProcess
from deepblender.codegen import CodePolicyViolation
from deepblender.domain.scene import BlenderScript


def test_worker_runs_command() -> None:
    result = WorkerProcess().run(WorkerCommand(argv=[sys.executable, "-c", "print(42)"]))
    assert result.ok
    assert result.stdout.strip() == "42"
    assert result.returncode == 0


def test_worker_timeout() -> None:
    result = WorkerProcess().run(
        WorkerCommand(argv=[sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.5)
    )
    assert result.returncode == -1
    assert "TIMEOUT" in result.stderr


def test_worker_missing_executable() -> None:
    result = WorkerProcess().run(WorkerCommand(argv=["definitely-not-a-real-binary-xyz"]))
    assert result.returncode == -1
    assert "not found" in result.stderr


def test_blender_bridge_requires_blender(tmp_path) -> None:  # noqa: ANN001
    bridge = BlenderBridge(blender_exe="definitely-not-blender")
    assert not bridge.available()
    script = BlenderScript(code="import bpy\n", scene_name="scene")
    with pytest.raises(BlenderNotFoundError):
        bridge.run_script(script, tmp_path)


def test_bridge_rejects_policy_violation_without_blender(tmp_path) -> None:  # noqa: ANN001
    """Fail-closed : un script non conforme est refusé avant toute exécution."""
    bridge = BlenderBridge(blender_exe="definitely-not-blender")
    script = BlenderScript(code="import os\nos.system('rm -rf /')\n", scene_name="evil")
    with pytest.raises(CodePolicyViolation):
        bridge.run_script(script, tmp_path)
    assert not list(tmp_path.iterdir())


def test_bridge_rejects_policy_violation_even_when_blender_present(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """La validation prime sur la disponibilité du binaire (fail-closed)."""
    monkeypatch.setenv("BLENDER_EXE", sys.executable)
    bridge = BlenderBridge()
    assert bridge.available()
    script = BlenderScript(code="import os\nos.system('rm -rf /')\n", scene_name="evil")
    with pytest.raises(CodePolicyViolation):
        bridge.run_script(script, tmp_path)
    assert not list(tmp_path.iterdir())
