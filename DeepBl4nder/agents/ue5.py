"""UE5Agent : transforme une SceneSpec en commandes REST pour UE5 (NOOA Agent).

L'UE5Agent génère une séquence de commandes REST qui, envoyées au serveur UE5,
créent la scène, les matériaux, l'éclairage, l'animation et le rendu dans
Unreal Engine 5 via Lumen, Nanite et MRQ.

Utilise le skill : unreal-engine.
"""

from __future__ import annotations

from typing import Any

from nooa import strategy
from nooa.agentdoc import hidden, pformat
from nooa.config.strategy_config import CodeActConfig
from nooa.strategy_validation import InvariantError

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, codeact_with_sandbox
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.domain.ue5 import UE5Command, UE5Commands
from DeepBl4nder.skills.registry import SkillRegistry


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

        scene_name = spec.brief[:50].replace(" ", "_").replace("'", "")
        commands: list[UE5Command] = []

        # 1. Create level
        commands.append(UE5Command(
            endpoint="level/create",
            payload={"name": scene_name, "template": "empty"},
        ))

        # 2. Create materials for environment
        env_materials = self._extract_materials_from_environment(spec.environment)
        for mat in env_materials:
            commands.append(UE5Command(
                endpoint="material/create",
                payload=mat,
            ))

        # 3. Create materials for characters
        for char in spec.characters:
            commands.append(UE5Command(
                endpoint="material/create",
                payload={
                    "name": f"Mat_{char.name}",
                    "base_color": [0.8, 0.8, 0.8],
                    "metallic": 0.0,
                    "roughness": 0.5,
                },
            ))

        # 4. Create ground plane
        commands.append(UE5Command(
            endpoint="actor/create",
            payload={
                "type": "StaticMeshActor",
                "name": "Ground",
                "transform": {"location": [0, 0, 0], "rotation": [0, 0, 0]},
            },
        ))

        # 5. Create character actors
        for char in spec.characters:
            pos_cm = [char.position[i] * 100 for i in range(3)]  # meters → centimeters
            commands.append(UE5Command(
                endpoint="actor/create",
                payload={
                    "type": "StaticMeshActor",
                    "name": char.name,
                    "transform": {"location": pos_cm, "rotation": [0, 0, 0]},
                    "asset": f"/Game/Characters/{char.name}",
                },
            ))

        # 6. Apply materials to characters
        for char in spec.characters:
            commands.append(UE5Command(
                endpoint="material/apply",
                payload={
                    "actor": char.name,
                    "material": f"Mat_{char.name}",
                },
            ))

        # 7. Setup lighting with Lumen
        lighting_preset = self._ue5_lighting_preset(spec.environment.lighting_mood)
        commands.append(UE5Command(
            endpoint="lighting/setup",
            payload={
                "lights": lighting_preset["lights"],
                "use_lumen": True,
                "skylight_intensity": lighting_preset["skylight_intensity"],
                "environment_color": list(lighting_preset["environment_color"]),
            },
        ))

        # 8. Create camera for first shot
        if spec.shots:
            shot = spec.shots[0]
            cam_pos_cm = [shot.camera.position[i] * 100 for i in range(3)]
            commands.append(UE5Command(
                endpoint="actor/create",
                payload={
                    "type": "CameraActor",
                    "name": "MainCamera",
                    "transform": {"location": cam_pos_cm, "rotation": list(shot.camera.rotation)},
                },
            ))

        # 9. Setup Sequencer for animation
        total_frames = sum(shot.frame_count() for shot in spec.shots)
        commands.append(UE5Command(
            endpoint="sequencer/setup",
            payload={
                "name": f"Seq_{scene_name}",
                "duration_frames": total_frames,
                "fps": spec.render.fps,
            },
        ))

        # 10. Add camera keyframes
        if spec.shots:
            current_frame = 0
            keyframes = []
            for shot in spec.shots:
                cam_pos_cm = [shot.camera.position[i] * 100 for i in range(3)]
                keyframes.append({
                    "frame": current_frame,
                    "location": cam_pos_cm,
                    "rotation": list(shot.camera.rotation),
                })
                current_frame += shot.frame_count()

            commands.append(UE5Command(
                endpoint="sequencer/add_camera",
                payload={
                    "sequence": f"Seq_{scene_name}",
                    "camera": "MainCamera",
                    "keyframes": keyframes,
                },
            ))

        # 11. Start render via MRQ
        commands.append(UE5Command(
            endpoint="render/start",
            payload={
                "output": f"/Game/RenderOutputs/{scene_name}",
                "sequence": f"Seq_{scene_name}",
                "resolution": list(spec.render.resolution),
                "format": "mp4",
                "quality": "cinematic",
            },
        ))

        return UE5Commands(
            scene_name=scene_name,
            commands=commands,
        )

    @hidden
    def _extract_materials_from_environment(self, environment) -> list[dict]:
        """Extrait les matériaux nécessaires de la description de l'environnement."""
        materials = []
        desc = environment.description.lower()

        # Ground material
        if any(w in desc for w in ["metal", "steel", "iron"]):
            materials.append({
                "name": "Mat_Ground",
                "base_color": [0.5, 0.5, 0.5],
                "metallic": 0.8,
                "roughness": 0.3,
            })
        elif any(w in desc for w in ["wood", "timber"]):
            materials.append({
                "name": "Mat_Ground",
                "base_color": [0.6, 0.4, 0.2],
                "metallic": 0.0,
                "roughness": 0.7,
            })
        elif any(w in desc for w in ["stone", "brick", "concrete"]):
            materials.append({
                "name": "Mat_Ground",
                "base_color": [0.4, 0.4, 0.4],
                "metallic": 0.0,
                "roughness": 0.8,
            })
        else:
            materials.append({
                "name": "Mat_Ground",
                "base_color": [0.3, 0.3, 0.3],
                "metallic": 0.0,
                "roughness": 0.6,
            })

        return materials

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

    def _ue5_lighting_preset(self, mood: str) -> dict:
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
