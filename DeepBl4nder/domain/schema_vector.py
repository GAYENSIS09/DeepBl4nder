"""Schema Vector Store : recherche sémantique des schémas de domaine.

Utilise TF-IDF + cosine similarity pour trouver les classes pertinentes
par rapport à un contexte donné (skills, brief, etc.).
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from DeepBl4nder.plugins.knowledge.knowledge_graph import KnowledgeGraphPlugin


class SchemaVectorStore:
    """Magasin vectoriel pour les schémas de domaine.

    Indexe les descriptions de classes et permet une recherche sémantique
    pour trouver les classes pertinentes par rapport à un contexte.
    """

    def __init__(self, kg: KnowledgeGraphPlugin) -> None:
        self._kg = kg
        self._vectorizer: TfidfVectorizer | None = None
        self._class_ids: list[str] = []
        self._class_texts: list[str] = []
        self._embeddings: np.ndarray | None = None
        self._built = False

    def build(self) -> None:
        """Construit l'index vectoriel à partir du KG."""
        graph = self._kg._read()

        self._class_ids = []
        self._class_texts = []
        self._class_data: dict[str, dict[str, Any]] = {}

        for node_id, node_data in graph.get("nodes", {}).items():
            if node_data.get("label") != "DomainClass":
                continue

            props = node_data.get("props", {})
            class_name = props.get("name", "")
            docstring = props.get("docstring", "")
            fields = props.get("fields", {})
            module = props.get("module", "")

            # Construire le texte descriptif pour l'indexation
            fields_str = ", ".join(fields.keys())
            field_types = " ".join(f"{k}:{v.get('type','')}" for k, v in fields.items())

            text = f"{class_name} {module} {docstring} {fields_str} {field_types}"
            text = re.sub(r'\s+', ' ', text.lower().strip())

            self._class_ids.append(node_id)
            self._class_texts.append(text)
            self._class_data[node_id] = {
                "name": class_name,
                "module": module,
                "docstring": docstring,
                "fields": fields,
            }

        if not self._class_texts:
            self._built = True
            return

        # Construire les embeddings TF-IDF
        self._vectorizer = TfidfVectorizer(
            max_features=512,
            stop_words=None,  # Garder les mots techniques
            ngram_range=(1, 2),
        )
        self._embeddings = self._vectorizer.fit_transform(self._class_texts)
        self._built = True

    def _ensure_built(self) -> None:
        """S'assure que l'index est construit."""
        if not self._built:
            self.build()

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Recherche les classes les plus pertinentes par rapport à la requête.

        Args:
            query: Texte de recherche (skills, brief, description de tâche).
            top_k: Nombre de résultats à retourner.

        Returns:
            Liste de dicts avec 'id', 'name', 'module', 'score', 'data'.
        """
        self._ensure_built()

        if not self._vectorizer or self._embeddings is None or not self._class_ids:
            return []

        query_text = re.sub(r'\s+', ' ', query.lower().strip())
        query_vec = self._vectorizer.transform([query_text])
        scores = cosine_similarity(query_vec, self._embeddings).flatten()

        # Trier par score décroissant
        top_indices = scores.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                break
            node_id = self._class_ids[idx]
            results.append({
                "id": node_id,
                "name": self._class_data[node_id]["name"],
                "module": self._class_data[node_id]["module"],
                "score": float(scores[idx]),
                "data": self._class_data[node_id],
            })

        return results

    def search_by_modules(
        self, query: str, modules: list[str], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Recherche dans des modules spécifiques.

        Args:
            query: Texte de recherche.
            modules: Noms de modules à filtrer (ex: ["narrative", "scene"]).
            top_k: Nombre de résultats.

        Returns:
            Liste de résultats filtrés par module.
        """
        self._ensure_built()

        if not self._vectorizer or self._embeddings is None or not self._class_ids:
            return []

        query_text = re.sub(r'\s+', ' ', query.lower().strip())
        query_vec = self._vectorizer.transform([query_text])
        scores = cosine_similarity(query_vec, self._embeddings).flatten()

        # Filtrer par module
        module_prefixes = [f"DeepBl4nder.domain.{m}" for m in modules]

        scored_indices = []
        for idx in range(len(self._class_ids)):
            module = self._class_data[self._class_ids[idx]]["module"]
            if any(module.endswith(m) or module == m for m in module_prefixes):
                scored_indices.append((idx, scores[idx]))

        # Trier par score
        scored_indices.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored_indices[:top_k]:
            if score <= 0:
                break
            node_id = self._class_ids[idx]
            results.append({
                "id": node_id,
                "name": self._class_data[node_id]["name"],
                "module": self._class_data[node_id]["module"],
                "score": score,
                "data": self._class_data[node_id],
            })

        return results


def format_classes_for_llm(
    classes: list[dict[str, Any]],
    max_classes: int = 8,
) -> str:
    """Formate les classes pour injection dans le prompt LLM.

    Args:
        classes: Liste de résultats de recherche vectorielle.
        max_classes: Nombre maximum de classes à inclure.

    Returns:
        Schéma formaté pour le LLM.
    """
    if not classes:
        return ""

    parts = []
    for cls in classes[:max_classes]:
        data = cls["data"]
        class_name = data.get("name", "")
        docstring = data.get("docstring", "")
        fields = data.get("fields", {})

        fields_text = "\n".join(
            f"  - {fname}: {finfo.get('type', 'Any')}"
            for fname, finfo in fields.items()
        )

        class_text = f"### {class_name}"
        if docstring:
            class_text += f"\n{docstring}"
        class_text += f"\n{fields_text}"

        parts.append(class_text)

    return "\n\n".join(parts)


# Singleton pour réutilisation
_store_instance: SchemaVectorStore | None = None


def get_vector_store(kg: KnowledgeGraphPlugin) -> SchemaVectorStore:
    """Retourne ou crée le magasin vectoriel singleton."""
    global _store_instance
    if _store_instance is None:
        _store_instance = SchemaVectorStore(kg)
        _store_instance.build()
    return _store_instance


def reset_vector_store() -> None:
    """Reset le singleton (utile pour les tests)."""
    global _store_instance
    _store_instance = None


def query_semantic_schema(
    kg: KnowledgeGraphPlugin,
    context: str,
    modules: list[str] | None = None,
    top_k: int = 8,
) -> str:
    """Interroge le magasin vectoriel et retourne le schéma formaté.

    Args:
        kg: Instance du KnowledgeGraphPlugin.
        context: Texte contextuel (skills + brief) pour la recherche.
        modules: Modules à filtrer (None = tous).
        top_k: Nombre de classes à retourner.

    Returns:
        Schéma formaté pour le LLM.
    """
    store = get_vector_store(kg)

    if modules:
        results = store.search_by_modules(context, modules, top_k=top_k)
    else:
        results = store.search(context, top_k=top_k)

    return format_classes_for_llm(results, max_classes=top_k)
