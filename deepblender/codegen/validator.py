"""Validation statique AST des scripts Blender générés.

Pipeline obligatoire : Python généré -> AST -> politique -> worker (Roadmap B §10).
Le validateur ne s'appuie que sur le module `ast` de la bibliothèque standard :
aucun appel réseau, aucune exécution.

Validation étendue (étape 6) :
- Checks sémantiques pour améliorer la qualité du rendu
- Avertissements si le script manque des éléments importants
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
    warnings: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    ast: ast.Module | None = None

    def add(self, error: str) -> None:
        self.errors.append(error)
        self.ok = False

    def warn(self, warning: str) -> None:
        self.warnings.append(warning)


class ASTValidator:
    """Analyse un script et le compare à la politique de code."""

    def __init__(self, policy: CodePolicy | None = None, strict: bool = False) -> None:
        self.policy = policy or CodePolicy()
        self.strict = strict  # Si True, les warnings deviennent des erreurs

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

        # Semantic quality checks (étape 6)
        self._check_semantic_quality(tree, source, report)

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

    def _check_semantic_quality(self, tree: ast.Module, source: str, report: ValidationReport) -> None:
        """Vérifications sémantiques pour améliorer la qualité du rendu."""
        source_lower = source.lower()

        # Check 1: scene.render.filepath must be set to absolute path
        if "scene.render.filepath" not in source:
            report.warn("scene.render.filepath not set - render output may fail")
        elif "//" in source:
            report.warn("Relative path '//' detected in filepath - may fail in headless mode")

        # Check 2: render engine should be set
        if "scene.render.engine" not in source:
            report.warn("scene.render.engine not set - defaulting to EEVEE")

        # Check 3: Check for compositing nodes
        has_compositing = (
            "bpy.context.scene.node_tree" in source
            or "CompositorNodeRLayers" in source
            or "compositing" in source_lower
        )
        if not has_compositing:
            report.warn("No compositing nodes detected - output may lack post-processing")

        # Check 4: Check for materials
        has_materials = (
            "bpy.data.materials" in source
            or "PrincipledBSDF" in source
            or "principled_bsdf" in source_lower
        )
        if not has_materials:
            report.warn("No materials created - scene may look flat")

        # Check 5: Check for camera setup
        has_camera = (
            "bpy.data.cameras" in source
            or "bpy.ops.object.camera_add" in source
            or "scene.camera" in source
        )
        if not has_camera:
            report.warn("No camera setup detected - render may fail")

        # Check 6: Sample count check
        if "samples" in source_lower:
            # Try to find sample value
            import re
            sample_match = re.search(r'samples\s*=\s*(\d+)', source)
            if sample_match:
                samples = int(sample_match.group(1))
                if samples < 128:
                    report.warn(f"Low sample count ({samples}) - consider 256+ for production quality")

        # Check 7: Denoising check
        if "denoising" not in source_lower and "use_denoising" not in source_lower:
            report.warn("Denoising not enabled - output may be noisy")

        # Check 8: Render passes for compositing
        has_passes = (
            "use_pass_z" in source
            or "use_pass_normal" in source
            or "use_pass_mist" in source
        )
        if not has_passes and has_compositing:
            report.warn("Compositing enabled but render passes not set - limited post-processing")

        # Promote warnings to errors in strict mode
        if self.strict and report.warnings:
            for w in report.warnings:
                report.errors.append(f"strict: {w}")
            report.ok = False


def validate_for_worker(source: str, policy: CodePolicy | None = None) -> ValidationReport:
    """Point d'entrée utilisé par les workers et le CLI."""
    return ASTValidator(policy).validate(source)


def validate_for_quality(source: str, policy: CodePolicy | None = None) -> ValidationReport:
    """Validation stricte pour la qualité de production."""
    return ASTValidator(policy, strict=True).validate(source)
