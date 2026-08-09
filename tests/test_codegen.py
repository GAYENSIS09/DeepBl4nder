"""Validateur AST et politique de code généré."""

from __future__ import annotations

from deepblender.codegen.policy import CodePolicy
from deepblender.codegen.validator import ASTValidator, validate_for_worker

SAFE_SCRIPT = (
    "import bpy\n"
    "import math\n\n"
    "bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))\n"
    "angle = math.radians(30.0)\n"
    "print(angle)\n"
)


def test_valid_script_passes() -> None:
    report = ASTValidator().validate(SAFE_SCRIPT)
    assert report.ok
    assert "bpy" in report.imports


def test_forbidden_import_fails() -> None:
    source = "import os\nos.listdir('.')\n"
    report = ASTValidator().validate(source)
    assert not report.ok
    assert any("os" in e for e in report.errors)


def test_forbidden_builtins_fail() -> None:
    for forbidden in ("exec", "eval"):
        report = ASTValidator().validate(f"{forbidden}('x')\n")
        assert not report.ok
        assert any(forbidden in e for e in report.errors)


def test_subprocess_call_fails() -> None:
    report = ASTValidator().validate("import subprocess\nsubprocess.run(['ls'])\n")
    assert not report.ok
    assert any("subprocess" in e for e in report.errors)


def test_syntax_error_fails() -> None:
    report = ASTValidator().validate("def broken(:\n")
    assert not report.ok
    assert any("syntax" in e for e in report.errors)


def test_source_too_long_fails() -> None:
    policy = CodePolicy(max_source_length=10)
    report = ASTValidator(policy).validate("import bpy\nimport math\n")
    assert not report.ok
    assert any("too long" in e for e in report.errors)


def test_worker_entrypoint() -> None:
    report = validate_for_worker(SAFE_SCRIPT)
    assert report.ok
