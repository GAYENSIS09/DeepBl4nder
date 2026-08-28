"""Démo : DirectorAgent avec un vrai LLM (Google Gemini par défaut).

Usage :
    python examples/run_director.py
"""

from __future__ import annotations

import asyncio

from DeepBl4nder.agents import DirectorAgent
from DeepBl4nder.domain.project import Brief


async def main() -> None:
    # from DeepBl4nder.llm import build_llm  # remplacé par local router
    from DeepBl4nder.llm_local import register_local_models, get_local_router

    register_local_models()
    # llm = build_llm()  # remplacé par local router
    llm = get_local_router(["qwen3-14b-q4"])
    print(f"Modèle : {llm.model}")
    director = DirectorAgent(llm=llm)
    brief = Brief(
        text=(
            "Une ruelle sombre sous la pluie, un personnage marche lentement "
            "vers une porte pendant cinq secondes."
        )
    )
    scene = await director.plan_scene(brief)
    print(f"SceneSpec : {scene.to_mapping()}")


if __name__ == "__main__":
    asyncio.run(main())
