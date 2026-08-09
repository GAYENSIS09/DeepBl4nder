"""Démo : DirectorAgent avec un vrai LLM (Google Gemini par défaut).

Usage :
    python examples/run_director.py
"""

from __future__ import annotations

import asyncio

from deepblender.agents import DirectorAgent
from deepblender.domain.project import Brief
from deepblender.llm import model_from_env


async def main() -> None:
    from deepblender.llm import build_llm

    llm = build_llm()
    print(f"Modèle : {model_from_env()}")
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
