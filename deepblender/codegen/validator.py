"""Validation statique AST des scripts Blender générés.

Pipeline obligatoire : Python généré -> AST -> politique -> worker (Roadmap B §10).
Le validateur ne s'appuie que sur le module `ast` de la bibliothèque standard :
aucun appel réseau, aucune exécution.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from deepblender.codegen.policy import CodePolicy

# Import de modules interdits, en dehors de la liste blanche.
_FORBIDDEN_ATTRS: tuple[tuple[str, str], ...] = (
    ("subprocess", "Popen"),
    ("subprocess", "run"),
    ("subprocess", "call"),
    ("os", "system"),
    ("os", "popen"),
)


@dataclass
class ValidationReport:
    """Résultat de la validation statique."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    ast: ast.Module | None = None

    def add(self, error: str) -> None:
        self.errors.append(error)
        self.ok = False


class ASTValidator:
    """Analyse un script et le compare à la politique de code."""

    def __init__(self, policy: CodePolicy | None = None) -> None:
        self.policy = policy or CodePolicy()

    def validate(self, source: str) -> ValidationReport:
        report = ValidationReport(ok=True)
        if len(source) > self.policy.max_source_length:
            report.add(f"source too long ({len(source)} > {self.policy.max_source_length})")
            return report
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            report.add(f"syntax error: {exc.msg} (line {exc.lineno})")
            return report
        report.ast = tree
        for node in ast.walk(tree):
            self._check_node(node, report)
        return report

    def _check_node(self, node: ast.AST, report: ValidationReport) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", maxsplit=1)[0]
                if top not in self.policy.allowed_imports:
                    report.add(f"import not allowed: {alias.name}")
                else:
                    report.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".", maxsplit=1)[0]
            if top not in self.policy.allowed_imports:
                report.add(f"import not allowed: from {module}")
            else:
                report.imports.append(module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.policy.forbidden_builtins:
                report.add(f"forbidden builtin call: {node.func.id}")
            if isinstance(node.func, ast.Attribute):
                attr = node.func
                parent = attr.value
                if isinstance(parent, ast.Name) and (parent.id, attr.attr) in _FORBIDDEN_ATTRS:
                    report.add(f"forbidden call: {parent.id}.{attr.attr}")
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if node.id in self.policy.forbidden_builtins and node.id != "__import__":
                report.add(f"forbidden name: {node.id}")

def validate_for_worker(source: str, policy: CodePolicy | None = None) -> ValidationReport:
    """Point d'entrée utilisé par les workers et le CLI."""
    return ASTValidator(policy).validate(source)
