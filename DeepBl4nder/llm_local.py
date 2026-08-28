"""Configuration LLM local (Ollama uniquement) pour DeepBl4nder.

Ne modifie PAS DeepBl4nder/llm.py — ce module étend le registre PROVIDERS
avec des presets Ollama et fournit des helpers de déploiement.

Usage:
    from DeepBl4nder.llm_local import get_local_router, ensure_model_pulled
    router = get_local_router(["qwen3-14b-q4"])

Variables d'environnement (.env) :
    LLM_BASE_URL=http://localhost:11434/v1     # Ollama (défaut)
    LLM_API_KEY=ollama                         # clé dummy pour Ollama
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any

from DeepBl4nder.llm import LLMProvider, LLMRouter, PROVIDERS


OLLAMA_URL = "http://localhost:11434/v1"


@dataclass(frozen=True)
class LocalModelSpec:
    name: str
    ollama_tag: str
    description: str
    vram_gb: float
    capabilities: tuple[str, ...]


LOCAL_MODELS: dict[str, LocalModelSpec] = {
    "qwen3-14b-q4": LocalModelSpec(
        name="qwen3-14b-q4",
        ollama_tag="qwen3:14b-q4_K_M",
        description="Qwen 3 14B quantifié 4-bit — usage général (Director, Story, QA, Coding)",
        vram_gb=9.0,
        capabilities=("chat", "coding", "reasoning"),
    ),
    "qwen3-8b-q4": LocalModelSpec(
        name="qwen3-8b-q4",
        ollama_tag="qwen3:8b-q4_K_M",
        description="Qwen 3 8B quantifié 4-bit — plus léger, fallback",
        vram_gb=5.5,
        capabilities=("chat", "coding"),
    ),
    "qwen2.5-coder-7b-q4": LocalModelSpec(
        name="qwen2.5-coder-7b-q4",
        ollama_tag="qwen2.5-coder:7b-q4_K_M",
        description="Qwen 2.5 Coder 7B — spécialisé code/Blender",
        vram_gb=4.5,
        capabilities=("coding",),
    ),
    "qwen2.5-vl-7b-q4": LocalModelSpec(
        name="qwen2.5-vl-7b-q4",
        ollama_tag="qwen2.5-vl:7b-q4_K_M",
        description="Qwen 2.5 VL 7B — vision multimodal (QA visuel, analyse renders)",
        vram_gb=5.5,
        capabilities=("vision", "chat"),
    ),
}


def _provider_id(spec: LocalModelSpec) -> str:
    return f"local-{spec.name}"


def build_local_provider(spec: LocalModelSpec) -> LLMProvider:
    return LLMProvider(
        id=_provider_id(spec),
        api_key_env="LLM_API_KEY",
        base_url=OLLAMA_URL,
        models=(f"ollama/{spec.ollama_tag}",),
    )


def register_local_models() -> dict[str, LLMProvider]:
    added = {}
    for spec in LOCAL_MODELS.values():
        provider = build_local_provider(spec)
        PROVIDERS[provider.id] = provider
        added[provider.id] = provider
    return added


def get_local_router(model_names: list[str] | None = None, **router_kwargs: Any) -> LLMRouter:
    if model_names is None:
        model_names = list(LOCAL_MODELS.keys())

    register_local_models()
    provider_ids = [_provider_id(LOCAL_MODELS[n]) for n in model_names if n in LOCAL_MODELS]
    # Pas de découverte dynamique : modèles fixes via tags Ollama
    return LLMRouter(provider_ids=provider_ids, discover=False, **router_kwargs)


def ensure_model_pulled(model_name: str, timeout: int = 600) -> bool:
    if model_name not in LOCAL_MODELS:
        raise ValueError(f"Modèle inconnu: {model_name}. Disponibles: {list(LOCAL_MODELS)}")

    spec = LOCAL_MODELS[model_name]
    tag = spec.ollama_tag

    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if tag.split(":")[0] in result.stdout:
            print(f"✅ {tag} déjà présent")
            return True

        print(f"⬇️  Pull {tag} (~{spec.vram_gb}GB)...")
        subprocess.run(["ollama", "pull", tag], check=True, timeout=timeout)
        print(f"✅ {tag} prêt")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Échec pull {tag}: {e}")
        return False
    except FileNotFoundError:
        print("❌ 'ollama' introuvable. Installer: https://ollama.ai")
        return False


def wait_for_ready(timeout: int = 60) -> bool:
    import httpx
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{OLLAMA_URL}/models", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def estimate_vram_usage(model_names: list[str]) -> float:
    return sum(LOCAL_MODELS[n].vram_gb for n in model_names if n in LOCAL_MODELS)


def recommend_setup(vram_gb: float = 8.0) -> dict[str, Any]:
    if vram_gb >= 12:
        models = ["qwen3-14b-q4", "qwen2.5-vl-7b-q4"]
    elif vram_gb >= 8:
        models = ["qwen3-14b-q4"]
    else:
        models = ["qwen3-8b-q4"]

    return {
        "models": models,
        "note": "Vision via fallback cloud si pas de modèle VL",
        "est_vram": estimate_vram_usage(models),
    }


def print_setup_guide() -> None:
    print("=" * 50)
    print("📦 DeepBl4nder — Setup LLM Local (Ollama)")
    print("=" * 50)

    rec = recommend_setup()
    print(f"\n🎯 Recommandation (VRAM ~8GB) :")
    print(f"   Modèles    : {', '.join(rec['models'])}")
    print(f"   VRAM estimée : {rec['est_vram']:.1f} GB")
    print(f"   Note       : {rec['note']}")

    print("\n📋 Étapes :")
    print("   1. Installer Ollama : https://ollama.ai")
    for m in rec["models"]:
        print(f"   2. ollama pull {LOCAL_MODELS[m].ollama_tag}")
    print("   3. ollama serve  (garde le serveur en arrière-plan)")
    print("   4. Dans .env :")
    print(f"      LLM_BASE_URL={OLLAMA_URL}")
    print(f"      LLM_API_KEY=ollama")

    print("\n🔧 Utilisation :")
    print("   from DeepBl4nder.llm_local import get_local_router")
    print(f"   router = get_local_router({rec['models']})")
    print("   # ou via build_llm existant :")
    print("   from DeepBl4nder.llm import build_llm")
    ids = [f"local-{m}" for m in rec["models"]]
    print(f"   llm = build_llm(provider_ids={ids})")


if __name__ == "__main__":
    print_setup_guide()