"""GodotAgent : transforme une SceneSpec en commandes REST pour Godot 4 (NOOA Agent).

Le GodotAgent génère une séquence de commandes REST qui, envoyées au serveur Godot,
créent la scène, les matériaux, l'éclairage, l'animation et le rendu dans
Godot 4 via GDScript.

Utilise le skill : godot-engine.
"""

from __future__ import annotations

from typing import Any

from nooa import strategy
from nooa.agentdoc import hidden, pformat
from nooa.config.strategy_config import CodeActConfig
from nooa.strategy_validation import InvariantError

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, codeact_with_sandbox
from DeepBl4nder.domain.godot import GodotCommands
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def godot_commands_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : GodotCommands doit contenir au moins une commande."""
    if not isinstance(result, GodotCommands):
        return
    if not result.commands:
        raise InvariantError(
            "GodotCommands doit contenir au moins une commande REST. "
            "Ajoutez scene/create, mesh/create, ou light/create."
        )


class GodotAgent(BaseAgent, DefaultsMixin):
    """You are a Godot 4 pipeline agent.

    You transform a typed SceneSpec into a sequence of REST commands that,
    sent to a Godot server, create the scene with PBR materials, lighting,
    animation and WebGL export.

    ## Skills available
    - godot-engine: GDScript, scenes, PBR materials, animation, WebGL export

    ## Rules
    - Generate deterministic command sequences (no randomness).
    - Use Godot 4 conventions (Node3D, StandardMaterial3D, etc.).
    - Commands must be valid REST endpoints for the Godot server.
    - Output MUST be valid GodotCommands (validated via postcondition).
    - Always create a scene first before adding meshes or materials.
    - Always set up lighting before rendering.
    - Use StandardMaterial3D for PBR materials.

    ## Command sequence
    The commands must follow this order:
    1. scene/create — create the scene
    2. mesh/create — create meshes (environment, characters, props)
    3. material/create — create PBR materials
    4. material/apply — apply materials to meshes
    5. camera/create — create cameras
    6. light/create — create lights
    7. lighting/setup — configure environment lighting
    8. animation/track — animate objects
    9. render/start — render the scene
    10. export — export to WebGL (optional)

    ## Godot Specifics
    - Godot uses meters as units (1 unit = 1 meter)
    - StandardMaterial3D for PBR (equivalent to Blender's Principled BSDF)
    - Node3D for 3D scene hierarchy
    - Tween for procedural animation
    - GDScript for custom behavior

    ## When to use Godot
    | Case                      | Godot | Blender |
    |---------------------------|-------|---------|
    | Rapid prototyping         | ✅    | ⚠️      |
    | Web scenes (WebGL)        | ✅    | ❌      |
    | Lightweight assets        | ✅    | ⚠️      |
    | Cinematic quality         | ❌    | ✅      |
    | Detailed characters       | ❌    | ✅      |
    | Heavy computation (physics)| ⚠️    | ✅      |

    ## Units
    - Godot uses meters (1 unit = 1 meter)
    - SceneSpec positions are already in meters (no conversion needed)
    - Rotation in degrees
    """

    def __init__(
        self,
        *args: Any,
        skill_registry: SkillRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        self._last_spec: SceneSpec | None = None
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(codeact_with_sandbox(CodeActConfig(
        postconditions=[godot_commands_postcondition],
        max_tokens=16384,
    )))
    async def build_commands(self, spec: SceneSpec) -> GodotCommands:  # type: ignore[return]
        """Turn the scene spec into Godot REST commands.

        Steps:
        1. Load godot-engine skill
        2. Analyze SceneSpec: environment, characters, shots
        3. Generate REST commands:
           - scene/create with scene name
           - mesh/create for environment meshes (ground, walls, etc.)
           - material/create for each material needed
           - material/apply to assign materials
           - camera/create for each camera
           - light/create for each light
           - lighting/setup for environment lighting
           - animation/track for object animations
           - render/start for final render
        4. Return GodotCommands
        """
        self._load_core_skills()
        self._load_skill("godot-engine")
        self._load_schema_context("scene", "godot")

        self._set_dynamic("scene_summary", "self._current_scene_summary(self._last_spec)")
        self._last_spec = spec
        ...

    @hidden
    def _current_scene_summary(self, spec: SceneSpec | None) -> str:
        """Résumé de la spec pour le contexte LLM."""
        if spec is None:
            return "no scene loaded"
        summary = {
            "brief": spec.brief,
            "environment": spec.environment.description,
            "lighting_mood": spec.environment.lighting_mood,
            "characters": [c.name for c in spec.characters],
            "shots": len(spec.shots),
            "engine": "GODOT",
            "resolution": spec.render.resolution,
            "fps": spec.render.fps,
        }
        return pformat(summary)

    def _godot_lighting_preset(self, mood: str) -> dict:
        """Convertit un lighting_mood en configuration Godot."""
        presets = {
            "neutral": {
                "lights": [
                    {"type": "directional", "name": "Sun", "energy": 2.0, "rotation": (-45, 0, 0)},
                ],
                "ambient_light_energy": 0.3,
                "use_glow": True,
            },
            "warm": {
                "lights": [
                    {"type": "directional", "name": "Sun", "energy": 2.5, "color": (1.0, 0.9, 0.7), "rotation": (-30, 0, 0)},
                    {"type": "omni", "name": "Fill", "energy": 1.0, "color": (1.0, 0.8, 0.5), "position": (2, -1, 2)},
                ],
                "ambient_light_energy": 0.2,
                "use_glow": True,
            },
            "cold": {
                "lights": [
                    {"type": "directional", "name": "Sun", "energy": 1.5, "color": (0.7, 0.8, 1.0), "rotation": (-60, 0, 0)},
                ],
                "ambient_light_energy": 0.4,
                "use_glow": True,
            },
            "dramatic": {
                "lights": [
                    {"type": "directional", "name": "Key", "energy": 3.0, "color": (1.0, 0.95, 0.9), "rotation": (-45, 0, -30)},
                    {"type": "spot", "name": "Rim", "energy": 4.0, "color": (0.5, 0.6, 1.0), "position": (-3, 2, 4)},
                ],
                "ambient_light_energy": 0.1,
                "use_glow": False,
            },
            "cinematic": {
                "lights": [
                    {"type": "directional", "name": "Key", "energy": 2.0, "rotation": (-45, 0, -20)},
                    {"type": "omni", "name": "Fill", "energy": 0.8, "color": (0.9, 0.9, 1.0), "position": (2, -1.5, 2)},
                    {"type": "spot", "name": "Back", "energy": 1.5, "color": (1.0, 0.95, 0.8), "position": (-2, 3, 3.5)},
                ],
                "ambient_light_energy": 0.15,
                "use_glow": True,
            },
        }
        return presets.get(mood, presets["neutral"])
