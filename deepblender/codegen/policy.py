"""Politique de code généré : périmètre autorisé pour les scripts Blender.

Le code généré par un LLM ne sort jamais du périmètre défini ici
(Roadmap B §10, C §14). Le validateur AST (`deepblender.codegen.validator`)
applique cette politique avant toute exécution dans un worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Modules autorisés dans un script Blender généré.
ALLOWED_IMPORTS: frozenset[str] = frozenset({"bpy", "math", "mathutils", "random", "json"})

# Appels et constructions toujours interdits.
FORBIDDEN_BUILTINS: frozenset[str] = frozenset({"exec", "eval", "compile", "open", "input", "__import__"})


class CodePolicyViolation(RuntimeError):
    """Un script a été refusé par la politique de code (fail-closed)."""


@dataclass(frozen=True)
class CodePolicy:
    """Politique : imports autorisés, appels interdits, ressources limitées."""

    allowed_imports: frozenset[str] = field(default_factory=lambda: ALLOWED_IMPORTS)
    forbidden_builtins: frozenset[str] = field(default_factory=lambda: FORBIDDEN_BUILTINS)
    max_source_length: int = 100_000
