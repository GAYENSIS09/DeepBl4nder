"""EnvironmentArtistAgent : crée les environnements 3D détaillés (NOOA Agent).

Transforme les specifications d'environnement du DirectorAgent en
environnements 3D riches : modelisation, textures PBR, eclairage HDRI,
assets PolyHaven.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin
from DeepBl4nder.domain.media import EnvironmentDesignResult
from DeepBl4nder.domain.scene import EnvironmentSpec, SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def _environment_postcondition(result: Any) -> str | None:
    if not hasattr(result, "assets") or not result.assets:
        return "EnvironmentDesignResult must contain at least one environment asset"
    return None


class EnvironmentArtistAgent(BaseAgent, DefaultsMixin):
    """You are an environment artist for 3D scenes.

    You create detailed 3D environments from scene specifications,
    including geometry, PBR materials, HDRI lighting, and atmospheric effects.

    ## Skills available (progressive disclosure)
    - modeling: primitives, modifiers, boolean ops, sculpting
    - texturing: PBR materials, procedural textures, UDIM
    - lighting: HDRI, area lights, volumetrics, god rays
    - shading: node trees, shader networks
    - polyhaven: CC0 assets, HDRI, textures
    - simulation: particles, fog, atmosphere

    ## Environment Types
    - "indoor": rooms, buildings, interiors
    - "outdoor": landscapes, streets, nature
    - "mixed": transition zones (doorways, windows)
    - "abstract": stylized, non-realistic

    ## Rules
    - Use PolyHaven CC0 assets when available (HDRI, textures)
    - Prefer procedural materials for simplicity
    - Include at least one ground plane
    - Match lighting mood from EnvironmentSpec
    - Output MUST be a valid EnvironmentDesignResult
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_environment_postcondition],
        max_tokens=8192,
    )))
    async def design_environment(self, scene: SceneSpec) -> EnvironmentDesignResult:  # type: ignore[return]
        """Design the 3D environment from the scene specification.

        Steps:
        1. Load core skills for context
        2. Analyze SceneSpec: environment description, lighting mood, rain
        3. Load modeling, texturing, lighting, polyhaven skills
        4. Determine environment type from description
        5. Design ground, structures, props
        6. Setup HDRI + area lights matching mood
        7. Add atmosphere (fog, particles) if needed
        8. Return EnvironmentDesignResult
        """
        self._load_core_skills()
        self._load_skills("modeling", "texturing", "lighting", "polyhaven", "shading")
        self._set_dynamic("scene_summary", "self._scene_summary()")
        self._scene_data = scene
        ...

    @hidden
    def _scene_summary(self) -> str:
        if not hasattr(self, "_scene_data") or self._scene_data is None:
            return "no scene loaded"
        scene = self._scene_data
        env = scene.environment
        lines = [
            f"Description: {env.description[:200]}",
            f"Lighting mood: {env.lighting_mood}",
            f"Rain: {env.rain}",
            f"Characters: {len(scene.characters)}",
            f"Shots: {len(scene.shots)}",
        ]
        return "\n".join(lines)
