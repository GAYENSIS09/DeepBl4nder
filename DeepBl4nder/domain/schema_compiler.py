"""Schema Compiler : compile le schéma de domaine en format compact.

Étape 2 du pipeline de gestion de contexte avancée.
Réduit les tokens en compilant les définitions de classes en format minimal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Cache des schémas compilés
_compiled_cache: dict[str, str] = {}


@dataclass
class CompiledClass:
    """Classe compilée en format compact."""
    name: str
    fields: list[tuple[str, str]]  # [(nom, type), ...]
    docstring_short: str = ""


class SchemaCompiler:
    """Étape 2: Compilation du schéma en format compact.

    Formats supportés:
    - "compact": StorySpec{logline:str,acts:list[Act]}  (minimal)
    - "readable": ### StorySpec\n- logline: str  (lisible mais optimisé)
    - "minimal": StorySpec(logline,acts,genre)  (noms seuls)
    """

    # Mappage des types longs vers des raccourcis
    TYPE_SHORTCUTS = {
        "list[str]": "[str]",
        "list[int]": "[int]",
        "list[float]": "[float]",
        "dict[str, str]": "{str:str}",
        "dict[str, Any]": "{str:Any}",
        "dict[str, float]": "{str:float}",
        "tuple[float, float, float]": "(f,f,f)",
        "tuple[int, int]": "(i,i)",
    }

    def compile(
        self,
        classes: list[dict[str, Any]],
        format: str = "compact",
    ) -> str:
        """Compile une liste de classes en format compact.

        Args:
            classes: Liste de dicts avec 'name', 'fields', 'docstring'.
            format: 'compact', 'readable', ou 'minimal'.

        Returns:
            Schéma compilé en texte.
        """
        if not classes:
            return ""

        if format == "compact":
            return self._compile_compact(classes)
        elif format == "readable":
            return self._compile_readable(classes)
        elif format == "minimal":
            return self._compile_minimal(classes)
        else:
            return self._compile_compact(classes)

    def _shorten_type(self, type_str: str) -> str:
        """Raccourcit un type long."""
        # Nettoyer d'abord
        cleaned = type_str.replace("typing.", "").replace("builtins.", "")
        return self.TYPE_SHORTCUTS.get(cleaned, cleaned)

    def _compile_compact(self, classes: list[dict[str, Any]]) -> str:
        """Format compact: ClassName{field1:type1,field2:type2}"""
        parts = []
        for cls in classes:
            name = cls.get("name", "")
            fields = cls.get("fields", {})
            doc = cls.get("docstring", "")

            # Extraire la première phrase de la docstring
            short_doc = doc.split(".")[0].strip() if doc else ""
            if len(short_doc) > 60:
                short_doc = short_doc[:57] + "..."

            fields_str = ",".join(
                f"{fname}:{self._shorten_type(finfo.get('type', 'Any'))}"
                for fname, finfo in fields.items()
            )

            if short_doc:
                parts.append(f"{name}{{{fields_str}}} # {short_doc}")
            else:
                parts.append(f"{name}{{{fields_str}}}")

        return "\n".join(parts)

    def _compile_readable(self, classes: list[dict[str, Any]]) -> str:
        """Format readable: optimisé mais lisible."""
        parts = []
        for cls in classes:
            name = cls.get("name", "")
            fields = cls.get("fields", {})
            doc = cls.get("docstring", "")

            # Docstring tronquée
            short_doc = doc.split(".")[0].strip() if doc else ""
            if len(short_doc) > 80:
                short_doc = short_doc[:77] + "..."

            lines = []
            if short_doc:
                lines.append(f"### {name} — {short_doc}")
            else:
                lines.append(f"### {name}")

            for fname, finfo in fields.items():
                ftype = self._shorten_type(finfo.get("type", "Any"))
                lines.append(f"  {fname}: {ftype}")

            parts.append("\n".join(lines))

        return "\n\n".join(parts)

    def _compile_minimal(self, classes: list[dict[str, Any]]) -> str:
        """Format minimal: noms seuls avec abréviations."""
        parts = []
        for cls in classes:
            name = cls.get("name", "")
            fields = cls.get("fields", {})
            field_names = list(fields.keys())
            parts.append(f"{name}({','.join(field_names)})")
        return " ".join(parts)

    def compile_from_vector_results(
        self,
        results: list[dict[str, Any]],
        format: str = "compact",
    ) -> str:
        """Compile les résultats de la recherche vectorielle.

        Args:
            results: Résultats de SchemaVectorStore.search().
            format: Format de sortie.

        Returns:
            Schéma compilé.
        """
        classes = [r.get("data", {}) for r in results]
        return self.compile(classes, format)

    def estimate_tokens(self, compiled: str) -> int:
        """Estime les tokens du schéma compilé."""
        return len(compiled) // 4 if compiled else 0


# Cache helper
def get_compiled_schema(
    classes: list[dict[str, Any]],
    format: str = "compact",
) -> str:
    """Retourne le schéma compilé (avec cache)."""
    # Clé de cache basée sur le contenu
    import hashlib
    content = str([(c.get("name", ""), list(c.get("fields", {}).keys())) for c in classes])
    cache_key = hashlib.md5(content.encode()).hexdigest()[:16] + f":{format}"

    if cache_key not in _compiled_cache:
        compiler = SchemaCompiler()
        _compiled_cache[cache_key] = compiler.compile(classes, format)

    return _compiled_cache[cache_key]


def clear_compile_cache() -> None:
    """Vide le cache de compilation."""
    _compiled_cache.clear()
