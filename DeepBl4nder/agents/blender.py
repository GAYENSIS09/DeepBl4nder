"""BlenderAgent : transforme une SceneSpec en actions Blender (NOOA Agent).

Le BlenderAgent génère du code bpy via CodeActStrategy. Le code généré passe par
le validateur AST (CodePolicy) avant exécution dans un worker Blender isolé.

Utilise les skills : blender-python, modeling, shading, rigging, animation,
camera, lighting, rendering, compositing, simulation, texturing, uv.

Charge automatiquement les assets (PolyHaven HDRI/textures, Quaternius/Mixamo characters)
pour améliorer la qualité de sortie au-delà des primitives.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, ReflexionStrategy, strategy
from nooa.agentdoc import hidden, pformat
from nooa.config.strategy_config import CodeActConfig, ReflexionConfig
from nooa.strategies.template import TemplateStrategy

from DeepBl4nder.agents.base import (
    BaseAgent,
    DefaultsMixin,
    blender_script_postcondition,
    codeact_with_sandbox,
)
from DeepBl4nder.domain.scene import BlenderScript, SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def _blender_reflexion_config() -> ReflexionConfig:
    """Config de réflexion : boucle courte, une itération de révision par défaut."""
    return ReflexionConfig(max_iterations=2)


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
    - rendering: settings, passes, denoising, output, FILEPATH
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

    ## CRITICAL: Output file path
    - The context variable ``render_dir`` contains the ABSOLUTE path where
      output files MUST be written (e.g. ``C:/runs/abc/render``).
    - ALWAYS set ``scene.render.filepath`` to an ABSOLUTE path inside
      ``render_dir``. Example:
      ``scene.render.filepath = render_dir + "/output.mp4"``
    - NEVER use relative paths with ``//`` prefix — they resolve to the
      .blend file location which does not exist in headless mode.
    - The runner scans ``render_dir`` for new media files after execution.
      If the file is written outside this directory, the render will fail
      with "No media file produced by Blender script".
    - For animations: set filepath to a prefix (no extension), e.g.
      ``scene.render.filepath = render_dir + "/frame_"`` then call
      ``bpy.ops.render.render(animation=True)``.
    - For stills: set filepath to a full path with extension, e.g.
      ``scene.render.filepath = render_dir + "/still.png"`` then call
      ``bpy.ops.render.render(write_still=True)``.

    ## CRITICAL: String formatting in generated code
    - Keep ALL string literals SHORT (max 80 chars).
    - Use triple-quoted strings for any text > 40 chars.
    - NEVER embed long French text or paragraphs in code.
    - For object names, use SHORT identifiers: "alley", "neon_sign", "rain_emitter".
    - For print/log messages, keep them under 60 chars.

    ## CRITICAL: Quality requirements
    You MUST produce commercial-quality output. Follow these rules:

    ### Render settings
    - Use Cycles engine with {samples} samples (256+ for production)
    - Enable denoising: scene.cycles.use_denoising = True
    - Use GPU if available: cycles.device = 'GPU' (fallback to 'CPU')
    - Resolution: {resolution}
    - Output format: OPEN_EXR_MULTILAYER (for compositing)

    ### Compositing nodes (MANDATORY)
    You MUST set up compositing nodes for every render:
    1. Render Layers node (input)
    2. Glare node (type='FOG_GLOW', quality='HIGH', threshold=0.8, size=7)
    3. Color Balance node (lift/gamma/gain based on lighting_mood)
    4. Lens Distortion (dispersion=0.005 for subtle chromatic aberration)
    5. Composite node (output)
    6. File Output node (save EXR with render passes)
    Enable render passes: Combined, Depth, Normal, Mist, AO

    ### Materials
    - Use image-based PBR textures when asset_paths are provided
    - Use Principled BSDF with proper roughness, metallic, normal maps
    - For procedural textures, use noise + colorramp for variation
    - Never use flat colors without any surface detail

    ### Characters
    - If asset_paths contain .glb/.fbx character files, import them:
      bpy.ops.import_scene.gltf(filepath=asset_path)
    - Position characters using their 'position' from SceneSpec
    - For animations, use NLA strips or keyframe the armature

    ### Lighting
    - If asset_paths contain .exr HDRI files, use them as world background
    - Set up 3-point lighting (key, fill, rim) matching lighting_mood
    - Use area lights for soft shadows, spot lights for dramatic effect

    ### Animation (single script, multi-shot)
    - ALL shots in ONE script using frame ranges
    - Shot N: frames [start_frame, end_frame]
    - Switch cameras by keyframing camera visibility or Track To constraint
    - Animate character positions with location keyframes

    ### Multi-shot pattern
    ```python
    # Setup scene once (environment, characters, lighting)
    # ...

    # Shot 1: frames 0 to {shot1_frames}
    cam1 = bpy.data.cameras['Shot1']
    cam1_obj = bpy.data.objects.new('Shot1', cam1)
    scene.collection.objects.link(cam1_obj)
    scene.camera = cam1_obj
    scene.frame_start = 0
    scene.frame_end = {shot1_frames}
    # Animate characters for shot 1...
    bpy.ops.render.render(animation=True)

    # Shot 2: frames {shot1_frames} to {shot1_frames + shot2_frames}
    cam2 = bpy.data.cameras['Shot2']
    cam2_obj = bpy.data.objects.new('Shot2', cam2)
    scene.collection.objects.link(cam2_obj)
    scene.camera = cam2_obj
    scene.frame_start = {shot1_frames}
    scene.frame_end = {shot1_frames + shot2_frames}
    # Animate characters for shot 2...
    bpy.ops.render.render(animation=True)
    ```

    ## Revision
    - On a QA revision, ``revision_feedback`` is set in context with the failing
      issues (kind, step, message) and recommendations. Address each issue
      explicitly in the regenerated script instead of replaying the same output.
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        self._last_spec: SceneSpec | None = None
        self._asset_paths: dict[str, str] = {}
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(codeact_with_sandbox(CodeActConfig(
        postconditions=[blender_script_postcondition],
        max_tokens=24576,
    )))
    async def build_script(self, spec: SceneSpec) -> BlenderScript:  # type: ignore[return]
        """Turn the scene spec into a deterministic Blender Python script.

        The context variable ``render_dir`` contains the ABSOLUTE path where
        output files MUST be written. ALWAYS set
        ``scene.render.filepath = render_dir + "/<filename>"`` before calling
        ``bpy.ops.render.render(...)``. NEVER use relative ``//`` paths.

        Steps:
        1. Load core skill summaries for context
        2. Download assets (HDRI, characters, textures) based on SceneSpec
        3. Inject asset paths into context for the LLM
        4. Load relevant skills (blender-python, modeling, shading, lighting, camera, rendering, animation, compositing)
        5. Generate Python code that:
           - Clears scene, sets render settings (fps, resolution, engine, denoising, GPU)
           - Creates environment (HDRI background, ground plane, rain particles if needed)
           - Creates/imports characters (.glb assets or primitives fallback)
           - For EACH shot in a single script: sets camera, lighting, animates characters
           - Sets up compositing nodes (glare, color balance, lens distortion)
           - Sets scene.render.filepath to an ABSOLUTE path inside render_dir
           - Enables render passes (Combined, Depth, Normal, Mist, AO)
        6. Return BlenderScript with code, scene_name, version
        """
        self._load_core_skills()

        # Load skills relevant to this spec
        self._load_skills(
            "blender-python",
            "modeling", "shading", "lighting", "camera", "rendering",
            "compositing",
        )
        if any(s.animation.description for s in spec.shots):
            self._load_skill("animation")
        self._load_schema_context("scene")

        # Download and inject assets
        self._download_assets(spec)

        # Inject asset paths into context
        self._set_context("asset_paths", self._format_asset_paths())
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
                max_tokens=24576,
            )),
            config=_blender_reflexion_config(),
        )
    )
    async def refine_script(
        self, spec: SceneSpec, revision_feedback: str, version: int = 1
    ) -> BlenderScript: # type: ignore[return]
        """Revise a generated Blender script from QA feedback.

        The context variable ``render_dir`` contains the ABSOLUTE path where
        output files MUST be written. ALWAYS set
        ``scene.render.filepath = render_dir + "/<filename>"`` before calling
        ``bpy.ops.render.render(...)``. NEVER use relative ``//`` paths.

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
            "modeling", "shading", "lighting", "camera", "rendering",
            "compositing",
        )
        self._load_schema_context("scene")
        self.context["revision_feedback"] = revision_feedback
        self.context["script_version"] = str(version)
        ...

    @hidden
    def _download_assets(self, spec: SceneSpec) -> None:
        """Télécharge les assets nécessaires (HDRI, characters, textures)."""
        self._asset_paths = {}

        # Download HDRI based on lighting mood
        try:
            from DeepBl4nder.assets.polyhaven import get_client
            polyhaven = get_client()
            mood_tags = {
                "warm": ["warm", "sunset"],
                "cold": ["cold", "winter", "blue"],
                "dramatic": ["dramatic", "dark", "stormy"],
                "cinematic": ["cinematic", "night", "urban"],
                "neutral": ["studio", "soft"],
            }
            tags = mood_tags.get(spec.environment.lighting_mood, [])
            hdris = polyhaven.search_hdris(tags=tags, limit=1)
            if hdris:
                hdri_path = polyhaven.download_hdri(hdris[0]["name"], resolution="1k")
                self._asset_paths["hdri"] = str(hdri_path)
        except Exception:
            pass

        # Download character assets
        try:
            from DeepBl4nder.assets.characters import get_character_client
            char_client = get_character_client()
            for char in spec.characters:
                if char.asset_id:
                    path = char_client.download(char.asset_id, source=char.asset_source or "quaternius")
                    self._asset_paths[f"character_{char.name}"] = str(path)
                elif not char.asset_id:
                    # Auto-select a character based on description
                    query = char.description or char.name
                    results = char_client.search_characters(query, limit=1)
                    if results:
                        path = char_client.download(results[0]["name"], source=results[0].get("source", "fallback"))
                        self._asset_paths[f"character_{char.name}"] = str(path)
        except Exception:
            pass

        # Download textures based on environment description
        try:
            from DeepBl4nder.assets.polyhaven import get_client
            polyhaven = get_client()
            desc = spec.environment.description.lower()
            tex_tags = []
            if any(w in desc for w in ["metal", "steel", "iron"]):
                tex_tags.append("metal")
            if any(w in desc for w in ["wood", "timber", "plank"]):
                tex_tags.append("wood")
            if any(w in desc for w in ["stone", "brick", "concrete"]):
                tex_tags.append("stone")
            if any(w in desc for w in ["water", "wet", "rain"]):
                tex_tags.append("water")
            if tex_tags:
                textures = polyhaven.search_textures(tags=tex_tags[:3], limit=3)
                for i, tex in enumerate(textures):
                    try:
                        tex_path = polyhaven.download_texture_map(tex["name"], map_type="diffuse")
                        self._asset_paths[f"texture_{i}"] = str(tex_path)
                    except Exception:
                        pass
        except Exception:
            pass

    @hidden
    def _format_asset_paths(self) -> str:
        """Formate les chemins d'assets pour le contexte LLM."""
        if not self._asset_paths:
            return "No assets available. Use procedural generation."
        lines = ["Available assets (use these absolute paths in bpy.ops.import):"]
        for key, path in self._asset_paths.items():
            lines.append(f"  {key}: {path}")
        return "\n".join(lines)

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
                "characters": [
                    f"{c.name} (asset={c.asset_id or 'none'})"
                    for c in spec.characters
                ],
                "shots": len(spec.shots),
                "render_samples": spec.render.samples,
                "render_denoise": spec.render.denoise,
                "render_gpu": spec.render.use_gpu,
                "assets_loaded": len(self._asset_paths),
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
