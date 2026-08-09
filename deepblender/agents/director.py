"""DirectorAgent : comprend un brief et produit des specs structurées (NOOA Agent).

Utilise CodeActStrategy pour générer du code Python qui construit la SceneSpec,
avec validation de sortie via output_model. Les skills (storyboard, cinematography,
lighting, composition) enrichissent le contexte par progressive disclosure.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.project import Brief
from deepblender.domain.scene import SceneSpec
from deepblender.skills.registry import SkillRegistry


class DirectorAgent(BaseAgent, DefaultsMixin):
    """You are a film director agent.

    You turn a creative brief into a structured, typed scene specification
    following the production pipeline (Brief -> SceneSpec -> ShotSpec).

    ## Skills available (progressive disclosure)
    - storyboard: plan shots with timing, camera, composition
    - cinematography: camera angles, lenses, movement
    - lighting: mood, key/fill/rim lights, color temperature
    - composition: rule of thirds, leading lines, depth

    ## Rules
    - Never write raw Blender Python yourself: produce typed specs.
    - Structure the intention: environment, characters, shots.
    - Keep shots short enough to stay within budget and render constraints.
    - Use skills to inform decisions; load full skill only when needed.
    - Output MUST be a valid SceneSpec (validated via output_model).
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        self.brief: Brief | None = None
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy())
    async def plan_scene(self, brief: Brief) -> SceneSpec:
        """Turn the creative brief into a structured scene specification.

        Steps:
        1. Load core skill summaries for context
        2. Analyze brief: extract mood, setting, characters, key actions
        3. Load relevant skills (storyboard, cinematography, lighting) as needed
        4. Generate Python code that constructs a SceneSpec with:
           - EnvironmentSpec (description, lighting_mood, rain)
           - CharacterSpec list (name, description, position)
           - ShotSpec list (duration, fps, camera, environment, characters, animation, lighting)
        5. Return the constructed SceneSpec
        """
        self.brief = brief
        self._load_core_skills()

        # Load skills relevant to this brief
        self._load_skills("storyboard", "cinematography", "lighting")

        # The CodeActStrategy will generate Python code to build the SceneSpec
        # Output is validated against SceneSpec type annotation
        ...
