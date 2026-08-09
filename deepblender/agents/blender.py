"""BlenderAgent : transforme une SceneSpec en actions Blender (NOOA Agent).

Le BlenderAgent génère du code bpy via CodeActStrategy. Le code généré passe par
le validateur AST (CodePolicy) avant exécution dans un worker Blender isolé.

Utilise les skills : blender-python, modeling, shading, rigging, animation,
camera, lighting, rendering, compositing, simulation, texturing, uv.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.scene import BlenderScript, SceneSpec
from deepblender.skills.registry import SkillRegistry


class BlenderAgent(BaseAgent, DefaultsMixin):
    """You are a Blender pipeline agent.

    You transform a typed SceneSpec into a deterministic Blender Python script
    (bpy) that builds the scene, places the camera, sets the lighting and
    optionally animates the shots.

    ## Skills available (progressive disclosure)
    - blender-python: safe bpy patterns, imports, reproducibility
    - modeling: primitives, modifiers, boolean, sculpting basics
    - shading: nodes, materials, PBR, procedural textures
    - rigging: armatures, bones, constraints, skinning
    - animation: keyframes, fcurves, drivers, NLA
    - camera: lenses, DOF, motion blur, stereo
    - lighting: HDRI, area/spot/sun lights, cycles/eevee
    - rendering: settings, passes, denoising, output
    - compositing: nodes, passes, grading, effects
    - simulation: rigid body, cloth, fluid, particles
    - texturing: UV, baking, painting, procedural
    - uv: unwrapping, packing, UDIM

    ## Rules
    - Generate reproducible scripts (fixed seed, explicit scene setup).
    - Use only the Blender Python API (bpy) and mathutils.
    - Never execute shell commands, never touch the filesystem outside the
      allowed work directory.
    - Inspect before destructive operations.
    - Output MUST be a valid BlenderScript (validated via output_model).
    - The generated code will be validated by AST validator (CodePolicy) before execution.
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        self.scene_name: str = ""
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy())
    async def build_script(self, spec: SceneSpec) -> BlenderScript:
        """Turn the scene spec into a deterministic Blender Python script.

        Steps:
        1. Load core skill summaries for context
        2. Analyze SceneSpec: environment, characters, shots
        3. Load relevant skills (blender-python, modeling, shading, lighting, camera, animation) as needed
        4. Generate Python code that:
           - Clears scene, sets render settings (fps, resolution, engine)
           - Creates environment (HDRI, ground plane, rain particles if needed)
           - Creates characters (imports assets or generates primitives)
           - For each shot: sets camera, lighting, animates characters/objects
           - Sets up render passes for compositing
        5. Return BlenderScript with code, scene_name, version
        """
        self._load_core_skills()

        # Load skills relevant to this spec
        self._load_skills("blender-python", "modeling", "shading", "lighting", "camera")
        if any(s.animation.description for s in spec.shots):
            self._load_skill("animation")

        # The CodeActStrategy will generate Python code to build the BlenderScript
        # Output is validated against BlenderScript type annotation
        ...
