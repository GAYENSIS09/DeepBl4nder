"""Schema Bootstrap : peuple le Knowledge Graph avec les schémas de domaine.

Lit les dataclasses du domaine et crée des nœuds/arithmiques dans le KG
pour permettre aux agents de récupérer les définitions de classes au runtime.
"""

from __future__ import annotations

import dataclasses
import inspect
from typing import Any

from DeepBl4nder.plugins.knowledge.knowledge_graph import KnowledgeGraphPlugin


# Modules de domaine à indexer
_DOMAIN_MODULES = {
    "narrative": "DeepBl4nder.domain.narrative",
    "scene": "DeepBl4nder.domain.scene",
    "qa": "DeepBl4nder.domain.qa",
    "media": "DeepBl4nder.domain.media",
    "asset": "DeepBl4nder.domain.asset",
    "ue5": "DeepBl4nder.domain.ue5",
    "godot": "DeepBl4nder.domain.godot",
    "ai_video": "DeepBl4nder.domain.ai_video",
}


def _format_type_annotation(annotation: Any) -> str:
    """Convertit une annotation de type en lisible pour le LLM."""
    if annotation is None:
        return "None"
    if isinstance(annotation, type):
        return annotation.__name__
    # handle list[X], dict[X, Y], etc.
    return str(annotation).replace("typing.", "").replace("builtins.", "")


def _extract_class_schema(cls: type) -> dict[str, Any]:
    """Extrait le schéma complet d'une dataclass."""
    if not dataclasses.is_dataclass(cls):
        return {}

    fields = {}
    for f in dataclasses.fields(cls):
        fields[f.name] = {
            "type": _format_type_annotation(f.type),
            "has_default": f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING,
        }

    methods = []
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        sig = inspect.signature(method)
        methods.append({
            "name": name,
            "signature": str(sig),
        })

    return {
        "name": cls.__name__,
        "module": cls.__module__,
        "docstring": (cls.__doc__ or "").strip(),
        "fields": fields,
        "methods": methods,
    }


def _import_module(module_path: str) -> Any:
    """Importe un module par son chemin complet."""
    import importlib
    return importlib.import_module(module_path)


def populate_schema(kg: KnowledgeGraphPlugin) -> None:
    """Peuple le KG avec les schémas de toutes les classes de domaine.

    Args:
        kg: Instance du KnowledgeGraphPlugin à peupler.
    """
    for module_name, module_path in _DOMAIN_MODULES.items():
        try:
            module = _import_module(module_path)
        except ImportError:
            continue

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if not dataclasses.is_dataclass(obj):
                continue
            if name.startswith("_"):
                continue

            schema = _extract_class_schema(obj)
            if not schema:
                continue

            node_id = f"class:{module_name}.{name}"
            kg.add_node(
                node_id=node_id,
                label="DomainClass",
                props=schema,
            )

            # Arêtes pour chaque champ
            for field_name, field_info in schema.get("fields", {}).items():
                field_node_id = f"field:{module_name}.{name}.{field_name}"
                kg.add_node(
                    node_id=field_node_id,
                    label="Field",
                    props={"name": field_name, **field_info},
                )
                kg.add_edge(
                    source=node_id,
                    target=field_node_id,
                    relation="has_field",
                )


def query_module_schema(kg: KnowledgeGraphPlugin, module_name: str) -> str:
    """Interroge le KG et formate le schéma d'un module pour le LLM.

    Args:
        kg: Instance du KnowledgeGraphPlugin.
        module_name: Nom du module (ex: "narrative", "scene").

    Returns:
        Schéma formaté sous forme de texte pour injection dans le prompt.
    """
    graph = kg._read()

    classes = []
    for node_id, node_data in graph.get("nodes", {}).items():
        if node_data.get("label") != "DomainClass":
            continue
        props = node_data.get("props", {})
        if props.get("module", "") != f"DeepBl4nder.domain.{module_name}":
            continue

        class_name = props.get("name", "")
        docstring = props.get("docstring", "")
        fields = props.get("fields", {})

        fields_text = "\n".join(
            f"  - {fname}: {finfo.get('type', 'Any')}"
            for fname, finfo in fields.items()
        )

        class_text = f"### {class_name}"
        if docstring:
            class_text += f"\n{docstring}"
        class_text += f"\n{fields_text}"

        classes.append(class_text)

    if not classes:
        return f"No schema found for module: {module_name}"

    return f"## Domain Schema - {module_name} module\n\n" + "\n\n".join(classes)


def query_classes_schema(kg: KnowledgeGraphPlugin, *module_names: str) -> str:
    """Interroge le KG pour plusieurs modules et formate le résultat.

    Args:
        kg: Instance du KnowledgeGraphPlugin.
        *module_names: Noms des modules à interroger.

    Returns:
        Schéma formaté pour tous les modules demandés.
    """
    parts = []
    for module_name in module_names:
        schema_text = query_module_schema(kg, module_name)
        parts.append(schema_text)
    return "\n\n".join(parts)
