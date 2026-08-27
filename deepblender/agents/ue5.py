"""UE5Agent : transforme une SceneSpec en commandes REST pour UE5 (NOOA Agent).

L'UE5Agent génère une séquence de commandes REST qui, envoyées au serveur UE5,
créent la scène, les matériaux, l'éclairage, l'animation et le rendu dans
Unreal Engine 5 via Lumen, Nanite et MRQ.

Utilise le skill : unreal-engine.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden, pformat
from nooa.config.strategy_config import CodeActConfig
from nooa.strategy_validation import InvariantError

from deepblender.agents.base import BaseAgent, DefaultsMixin, codeact_with_sandbox
from deepblender.domain.scene import SceneSpec
from deepblender.domain.ue5 import UE5Command, UE5Commands
from deepblender.skills.registry import SkillRegistry


def ue5_commands_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : UE5Commands doit contenir au moins une commande."""
    if not isinstance(result, UE5Commands):
        return
    if not result.commands:
        raise InvariantError(
            "UE5Commands doit contenir au moins une commande REST. "
            "Ajoutez level/create, material/create, ou lighting/setup."
        )


class UE5Agent(BaseAgent, DefaultsMixin):
    """You are an Unreal Engine 5 pipeline agent.

    You transform a typed SceneSpec into a sequence of REST commands that,
    sent to a UE5 server, create the scene with Lumen lighting, Nanite
    geometry, and MRQ rendering.

    ## Skills available
    - unreal-engine: UE5 Python API, MRQ, Sequencer, Lumen, materials

    ## Rules
    - Generate deterministic command sequences (no randomness).
    - Use the UE5 Python API conventions (unreal module patterns).
    - Commands must be valid REST endpoints for the UE5 server.
    - Output MUST be a valid UE5Commands (validated via postcondition).
    - Always create a level first before adding actors or materials.
    - Always set up lighting before rendering.
    - Use Lumen for GI (not baked lighting).
    - Use Nanite for complex geometry (not for transparent materials).

    ## CRITICAL: Command sequence
    The commands must follow this order:
    1. level/create — create the level
    2. asset/import — import characters, HDRI, textures (if any)
    3. material/create — create PBR materials
    4. material/apply — apply materials to actors
    5. actor/create — create actors (characters, props, cameras)
    6. lighting/setup — configure Lumen lighting
    7. sequencer/setup — set up animation sequence
    8. sequencer/add_camera — add camera keyframes
    9. sequencer/add_actor_track — animate actors
    10. render/start — render via MRQ

    ## UE5 Specifics
    - Lumen GI: use_lumen=True in lighting/setup
    - Nanite: enabled by default for static meshes
    - MRQ: Movie Render Queue for high-quality offline rendering
    - Sequencer: timeline-based animation with keyframes
    - Console Variables: use for quality tweaks (r.Lumen.*, r.Nanite.*)

    ## Units
    - UE5 uses centimeters (1 meter = 100 units)
    - Convert SceneSpec positions (meters) to UE5 units (×100)
    - Rotation in degrees (not radians)
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
        postconditions=[ue5_commands_postcondition],
        max_tokens=16384,
    )))
    async def build_commands(self, spec: SceneSpec) -> UE5Commands:  # type: ignore[return]
        """Turn the scene spec into UE5 REST commands.

        Steps:
        1. Load unreal-engine skill
        2. Analyze SceneSpec: environment, characters, shots
        3. Convert units (meters → centimeters for UE5)
        4. Generate REST commands:
           - level/create with scene name
           - asset/import for characters and textures
           - material/create for each material needed
           - actor/create for each character and camera
           - lighting/setup with Lumen GI
           - sequencer/setup with camera and actor tracks
           - render/start with MRQ settings
        5. Return UE5Commands
        """
        self._load_core_skills()
        self._load_skill("unreal-engine")

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
            "engine": "UE5",
            "use_lumen": spec.render.ue5.use_lumen if spec.render.ue5 else True,
            "use_nanite": spec.render.ue5.use_nanite if spec.render.ue5 else True,
            "resolution": spec.render.resolution,
            "fps": spec.render.fps,
        }
        return pformat(summary)
        """Convertit un lighting_mood en configuration UE5 Lumen."""
        presets = {
            "neutral": {
                "lights": [
                    {"type": "DirectionalLight", "name": "Sun", "intensity": 10.0, "rotation": (45, 0, 0)},
                ],
                "skylight_intensity": 1.0,
                "environment_color": (0.1, 0.1, 0.15),
            },
            "warm": {
                "lights": [
                    {"type": "DirectionalLight", "name": "Sun", "intensity": 12.0, "color": (1.0, 0.9, 0.7), "rotation": (30, 0, 0)},
                    {"type": "PointLight", "name": "Fill", "intensity": 5.0, "color": (1.0, 0.8, 0.5), "location": (200, -100, 200)},
                ],
                "skylight_intensity": 0.8,
                "environment_color": (0.15, 0.1, 0.05),
            },
            "cold": {
                "lights": [
                    {"type": "DirectionalLight", "name": "Sun", "intensity": 8.0, "color": (0.7, 0.8, 1.0), "rotation": (60, 0, 0)},
                    {"type": "SkyLight", "name": "Sky", "intensity": 1.2, "color": (0.6, 0.7, 0.9)},
                ],
                "skylight_intensity": 1.2,
                "environment_color": (0.05, 0.08, 0.15),
            },
            "dramatic": {
                "lights": [
                    {"type": "DirectionalLight", "name": "Key", "intensity": 15.0, "color": (1.0, 0.95, 0.9), "rotation": (45, 0, -30)},
                    {"type": "SpotLight", "name": "Rim", "intensity": 20.0, "color": (0.5, 0.6, 1.0), "location": (-300, 200, 400), "rotation": (0, 0, 180)},
                ],
                "skylight_intensity": 0.3,
                "environment_color": (0.02, 0.02, 0.05),
            },
            "cinematic": {
                "lights": [
                    {"type": "DirectionalLight", "name": "Key", "intensity": 10.0, "rotation": (45, 0, -20)},
                    {"type": "PointLight", "name": "Fill", "intensity": 3.0, "color": (0.9, 0.9, 1.0), "location": (200, -150, 200)},
                    {"type": "SpotLight", "name": "Back", "intensity": 8.0, "color": (1.0, 0.95, 0.8), "location": (-200, 300, 350), "rotation": (0, 0, 180)},
                ],
                "skylight_intensity": 0.5,
                "environment_color": (0.05, 0.05, 0.08),
            },
        }
        return presets.get(mood, presets["neutral"])
