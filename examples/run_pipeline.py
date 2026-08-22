"""Démo : pipeline complet Brief -> SceneSpec -> BlenderScript (LLM réel).

Le script bpy généré est validé statiquement (AST + politique de code) mais
n'est pas exécuté : le rendu réel nécessite un worker Blender (Docker).

Usage :
    python examples/run_pipeline.py
"""

from __future__ import annotations

import asyncio

from deepblender.agents import BlenderAgent, DirectorAgent
from deepblender.codegen.validator import validate_for_worker
from deepblender.domain.project import Brief
from deepblender.llm import build_llm


async def main() -> None:
    llm = build_llm()
    print(f"Modèle : {llm.model()}")

    brief = Brief(
        text=(
            "Une ruelle sombre sous la pluie, un personnage marche lentement "
            "vers une porte pendant cinq secondes."
        )
    )

    director = DirectorAgent(llm=llm)
    scene = await director.plan_scene(brief)
    print(f"SceneSpec : {scene.to_mapping()}")

    blender = BlenderAgent(llm=llm)
    script = await blender.build_script(scene)
    print(f"BlenderScript v{script.version} : {script.scene_name!r}")
    print("--- début du script ---")
    print("\n".join(script.code.splitlines()[:12]))
    print("...")

    report = validate_for_worker(script.code)
    status = "OK" if report.ok else "REJETÉ"
    print(f"Validation AST : {status} ({len(report.errors)} erreur(s))")
    for error in report.errors:
        print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main())
