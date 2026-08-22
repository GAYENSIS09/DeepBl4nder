"""BlenderAgent : transforme une SceneSpec en actions Blender (NOOA Agent).

Le BlenderAgent génère du code bpy via CodeActStrategy. Le code généré passe par
le validateur AST (CodePolicy) avant exécution dans un worker Blender isolé.

Utilise les skills : blender-python, modeling, shading, rigging, animation,
camera, lighting, rendering, compositing, simulation, texturing, uv.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, ReflexionStrategy, strategy
from nooa.agentdoc import hidden, pformat
from nooa.config.strategy_config import CodeActConfig, ReflexionConfig
from nooa.strategies.template import TemplateStrategy

from deepblender.agents.base import (
    BaseAgent,
    DefaultsMixin,
    blender_script_postcondition,
    codeact_with_sandbox,
)
from deepblender.domain.scene import BlenderScript, SceneSpec
from deepblender.skills.registry import SkillRegistry


def _blender_reflexion_config() -> ReflexionConfig:
    """Config de réflexion : boucle courte, une itération de révision par défaut."""
    return ReflexionConfig(max_iterations=1)


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

    ## CRITICAL: String formatting in generated code
    - Keep ALL string literals SHORT (max 80 chars).
    - Use triple-quoted strings for any text > 40 chars.
    - NEVER embed long French text or paragraphs in code.
    - For object names, use SHORT identifiers: "alley", "neon_sign", "rain_emitter".
    - For print/log messages, keep them under 60 chars.

    ## Revision
    - On a QA revision, ``revision_feedback`` is set in context with the failing
      issues (kind, step, message) and recommendations. Address each issue
      explicitly in the regenerated script instead of replaying the same output.
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        self._last_spec: SceneSpec | None = None
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(codeact_with_sandbox(CodeActConfig(
        postconditions=[blender_script_postcondition],
        max_tokens=16384,
    )))
    async def build_script(self, spec: SceneSpec) -> BlenderScript:  # type: ignore[return]
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
        self._load_skills(
            "blender-python",
            "modeling", "shading", "lighting", "camera",
        )
        if any(s.animation.description for s in spec.shots):
            self._load_skill("animation")

        # The CodeActStrategy will generate Python code to build the BlenderScript
        # Output is validated against BlenderScript type annotation
        self._set_dynamic("scene_summary", "self._current_scene_summary(self._last_spec)")
        self._last_spec = spec
        ...

    @strategy(TemplateStrategy())
    async def build_probe_script(self, scene_name: str) -> BlenderScript:
        """Generate a deterministic capability probe for scene {scene_name}.

        The probe is a read-only Blender script (no scene mutation) that lists
        the objects, materials, lights and cameras currently in the .blend file
        so downstream steps can validate assumptions before building anything.
        """
        code = (
            "import bpy\n"
            "for obj in bpy.data.objects:\n"
            f"    print(f'{scene_name} | {{obj.name}} | {{obj.type}}')\n"
            "print('materials:', len(bpy.data.materials))\n"
            "print('lights:', sum(1 for o in bpy.data.objects if o.type == 'LIGHT'))\n"
            "print('cameras:', sum(1 for o in bpy.data.objects if o.type == 'CAMERA'))\n"
        )
        return BlenderScript(code=code, scene_name=scene_name)

    @strategy(
        ReflexionStrategy(
            base=CodeActStrategy(config=CodeActConfig(
                postconditions=[blender_script_postcondition],
                max_tokens=16384,
            )),
            config=_blender_reflexion_config(),
        )
    )
    async def refine_script(
        self, spec: SceneSpec, revision_feedback: str, version: int = 1
    ) -> BlenderScript: # type: ignore[return]
        """Revise a generated Blender script from QA feedback.

        Steps:
        1. Load core skills and the revision feedback (kind, step, message)
        2. Identify which shot/object the feedback targets
        3. Regenerate only the affected code paths
        4. Keep the script deterministic and reproducible (fixed seed)
        5. Bump ``version`` and return BlenderScript
        """
        self._load_core_skills()
        self._load_skills(
            "blender-python", "blender-api-reference",
            "modeling", "shading", "lighting", "camera",
        )
        self.context.set("revision_feedback", revision_feedback)
        self.context.set("script_version", str(version))
        ...

    @hidden
    def _current_scene_summary(self, spec: SceneSpec | None) -> str:
        """Résumé compact de la spec (rendu agentdoc) pour le contexte dynamique."""
        if spec is None:
            return "no scene loaded"
        return pformat(
            {
                "brief": spec.brief,
                "environment": spec.environment.description,
                "lighting_mood": spec.environment.lighting_mood,
                "rain": spec.environment.rain,
                "characters": [c.name for c in spec.characters],
                "shots": len(spec.shots),
            }
        )

    @hidden
    def recent_run_history(self, limit: int = 5) -> list[str]:
        """Derniers événements NOOA de l'agent, résumés pour le modèle."""
        rows: list[str] = []
        for event in self.events.query(limit=limit):
            content = getattr(event, "content", None) or ""
            rows.append(f"[{getattr(event, 'type', 'event')}] {content}")
        return rows

    @hidden
    def validate_script(self, script: BlenderScript) -> list[str]:
        """Contrôles déterministes d'un BlenderScript (utilisables en tests)."""
        problems: list[str] = []
        if not (script.code or "").strip():
            problems.append("code vide")
        if not script.scene_name:
            problems.append("scene_name vide")
        return problems
