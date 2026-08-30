"""Script de téléchargement des modèles GGUF depuis Hugging Face.

Usage:
    python -m DeepBl4nder.llm.download
    python -m DeepBl4nder.llm.download --model qwen3-8b
    python -m DeepBl4nder.llm.download --all
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from DeepBl4nder.llm.model_registry import MODELS, LocalModel


def get_models_dir() -> Path:
    """Répertoire de destination des modèles."""
    return Path(os.getenv("DeepBl4nder_MODELS_DIR", "models"))


def download_model(model: LocalModel, force: bool = False) -> Path:
    """Télécharge un modèle GGUF depuis Hugging Face."""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        raise RuntimeError(
            "huggingface-hub non installé. "
            "Installez-le avec : pip install 'DeepBl4nder[local-llm]'"
        )

    dest = get_models_dir()
    dest.mkdir(parents=True, exist_ok=True)

    target = dest / model.gguf_filename
    if target.exists() and not force:
        print(f"✓ {model.id} déjà présent : {target}")
        return target

    print(f"↓ Téléchargement de {model.id} ({model.huggingface_repo})...")
    print(f"  Fichier : {model.huggingface_file}")
    print(f"  Destination : {target}")

    path = hf_hub_download(
        repo_id=model.huggingface_repo,
        filename=model.huggingface_file,
        local_dir=str(dest),
        local_dir_use_symlinks=False,
    )

    # hf_hub_download peut retourner un sous-dossier
    downloaded = Path(path)
    if downloaded != target:
        downloaded.rename(target)

    print(f"✓ {model.id} téléchargé : {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Télécharge les modèles GGUF pour DeepBl4nder LLM local"
    )
    parser.add_argument(
        "--model", "-m",
        choices=list(MODELS.keys()),
        help="Modèle à télécharger",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Télécharger tous les modèles",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Lister les modèles disponibles",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Forcer le re-téléchargement",
    )
    args = parser.parse_args()

    if args.list:
        print("Modèles disponibles :")
        for mid, model in MODELS.items():
            exists = "✓" if model.gguf_path.exists() else "✗"
            print(f"  {exists} {mid:12s} | {model.vram_gb:4.1f} GB VRAM | {model.description}")
        return

    if args.all:
        for model in MODELS.values():
            download_model(model, force=args.force)
        return

    if args.model:
        download_model(MODELS[args.model], force=args.force)
        return

    # Par défaut: télécharger tous les modèles manquants
    downloaded = 0
    for model in MODELS.values():
        if not model.gguf_path.exists():
            download_model(model, force=args.force)
            downloaded += 1
    if downloaded == 0:
        print("Tous les modèles sont déjà téléchargés.")


if __name__ == "__main__":
    main()
