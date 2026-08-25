"""CharacterDesignerAgent : conçoit les personnages 3D (NOOA Agent).

Transforme les CharacterSpec du DirectorAgent en specifications détaillées
de personnages 3D : géométrie, matériaux, squelette, expressions faciales.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.scene import CharacterSpec, SceneSpec
from deepblender.skills.registry import SkillRegistry


# Postcondition: CharacterDesignResult must have at least one character
def _character_design_postcondition(result: Any) -> str | None:
    if not hasattr(result, "characters") or not result.characters:
        return "CharacterDesignResult must contain at least one character design"
    return None


class CharacterDesignResult:
    """Résultat de la conception de personnages."""

    def __init__(
        self,
        characters: list[CharacterModel],
        style: str = "realistic",
        scale: float = 1.0,
    ) -> None:
        self.characters = characters
        self.style = style
        self.scale = scale

    def to_mapping(self) -> dict[str, Any]:
        return {
            "characters": [c.to_mapping() for c in self.characters],
            "style": self.style,
            "scale": self.scale,
        }


class CharacterModel:
    """Modèle de personnage 3D."""

    def __init__(
        self,
        name: str,
        description: str,
        geometry_type: str = "primitive",
        material: str | None = None,
        skeleton_type: str | None = None,
        blendshapes: list[str] | None = None,
        scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
        import_path: str | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.geometry_type = geometry_type
        self.material = material
        self.skeleton_type = skeleton_type
        self.blendshapes = blendshapes or []
        self.scale = scale
        self.import_path = import_path

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "geometry_type": self.geometry_type,
            "material": self.material,
            "skeleton_type": self.skeleton_type,
            "blendshapes": self.blendshapes,
            "scale": list(self.scale),
            "import_path": self.import_path,
        }


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
        """
        self._load_core_skills()
        self._load_skills("character-design", "modeling", "shading", "rigging")
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
