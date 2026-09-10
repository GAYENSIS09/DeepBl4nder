"""CharacterDesignerAgent : conçoit les personnages 3D (NOOA Agent).

Transforme les CharacterSpec du DirectorAgent en specifications détaillées
de personnages 3D : géométrie, matériaux, squelette, expressions faciales.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, InvariantError
from DeepBl4nder.domain.media import CharacterDesignResult, CharacterModel  # noqa: F401  # exposé dans le sandbox
from DeepBl4nder.domain.scene import CharacterSpec, SceneSpec  # noqa: F401  # CharacterSpec exposé dans le sandbox
from DeepBl4nder.skills.registry import SkillRegistry


# Postcondition: CharacterDesignResult must have at least one character
def _character_design_postcondition(_agent: BaseAgent | None, result: Any, call: Any) -> None:
    if not isinstance(result, CharacterDesignResult):
        return
    if not result.characters:
        raise InvariantError(
            "CharacterDesignResult.characters ne doit pas être vide : appelez "
            'return_result avec characters=[{"name": "Héros", "description": '
            '"jeune hackeuse", "geometry_type": "primitive", "material": '
            '"PBR_Skin"}] — la liste characters ne doit pas être vide.'
        )


class CharacterDesignerAgent(BaseAgent, DefaultsMixin):
    """You are a character design agent for 3D animation.

    You transform character specifications from the DirectorAgent into
    detailed 3D character models ready for animation.

    ## Skills available (progressive disclosure)
    - character-design: character proportions, styles, pipelines
    - modeling: primitives, modifiers, sculpting basics
    - rigging: armatures, bones, constraints
    - shading: PBR materials, procedural textures
    - vrm-pipeline: VRM avatar format, morph targets

    ## Rules
    - Choose the simplest geometry that fits the art style
    - Prefer primitives for prototyping, detailed meshes for final
    - Always include material/shading specification
    - Mark characters needing external assets (import_path)
    - NEVER `import bpy` in the execution cell: the sandbox has no Blender
      Python, so `ModuleNotFoundError` is raised and the turn is lost. Just
      build and return `CharacterDesignResult(characters=[CharacterModel(...)])`.
    - Output MUST be a valid CharacterDesignResult

    ## Character Types
    - "hero": Main character, highest detail
    - "support": Supporting characters, medium detail
    - "background": Crowd/extras, lowest detail (instanced)

    ## Geometry Types
    - "primitive": Blender primitives (cube, sphere, cylinder)
    - "detailed": Custom mesh with modifiers
    - "import": External asset (OBJ/FBX/glTF via import_path)
    - "vrm": VRM avatar (for cross-platform compatibility)
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_character_design_postcondition],
        max_tokens=8192,
    )))
    async def design_characters(self, scene: SceneSpec) -> CharacterDesignResult:  # type: ignore[return]
        """Design 3D characters from the scene specification.

        Steps:
        1. Load core skills for context
        2. Analyze SceneSpec characters: names, descriptions, roles
        3. Load character-design and modeling skills
        4. For each character, determine:
           - Geometry type (primitive/detailed/import/vrm)
           - Material properties (color, roughness, metallic)
           - Skeleton type (if animated)
           - Blendshapes (if facial expressions needed)
           - Import path (if external asset)
        5. Return CharacterDesignResult with all character models

        ## CRITICAL: Types available in the sandbox
        - ONLY these domain types exist: ``CharacterDesignResult``,
          ``CharacterModel``, ``CharacterSpec``, ``SceneSpec``. There is NO
          ``MaterialProperties`` type — do not import or reference it. Use the
          plain ``material`` string field of ``CharacterModel`` instead
          (e.g. ``material="PBR_Skin"``).
        - NEVER use ``__dict__``, ``vars(...)`` or ``__dataclass_fields__``:
          the sandbox forbids dunder access. Read fields via attributes.

        ## CRITICAL: How to end the turn
        - ALWAYS end your reply by calling ``return_result(result)`` where
          ``result`` is a CharacterDesignResult instance you built.
        - NEVER end with plain text or a bare execute_python cell: the turn is
          rejected ("failed") and you waste a full retry.
        - At least one character is required (postcondition): pass a non-empty
          ``characters=[CharacterModel(...)]`` list before returning.
        """
        self._load_core_skills()
        self._load_skills("character-design", "modeling", "shading", "rigging")
        self._load_schema_context("scene", "media")
        self._set_dynamic("scene_summary", "self._scene_summary()")
        self._scene_data = scene
        ...

    @hidden
    def _scene_summary(self) -> str:
        if not hasattr(self, "_scene_data") or self._scene_data is None:
            return "no scene loaded"
        scene = self._scene_data
        chars = [f"{c.name}: {c.description[:60]}" for c in scene.characters]
        return f"Characters: {len(chars)}\n" + "\n".join(chars)
