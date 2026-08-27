"""DirectorAgent : comprend un brief et produit des specs structurées (NOOA Agent).

Utilise CodeActStrategy pour générer du code Python qui construit la SceneSpec,
avec validation de sortie via output_model. Les skills (storyboard, cinematography,
lighting, composition) enrichissent le contexte par progressive disclosure.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, scene_spec_postcondition
from DeepBl4nder.domain.project import Brief
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.domain.narrative import StorySpec, StoryboardSpec
from DeepBl4nder.skills.registry import SkillRegistry


class DirectorAgent(BaseAgent, DefaultsMixin):
    """You are a film director agent.

    You turn a creative brief (and optionally a StorySpec + StoryboardSpec)
    into a structured, typed scene specification following the production
    pipeline (Brief -> SceneSpec -> ShotSpec).

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

    ## CRITICAL: String formatting in generated code
    - Keep ALL description strings SHORT (max 60 chars). Summarize, do not quote.
    - Use triple-quoted strings ONLY for brief descriptions, never for long text.
    - NEVER embed full paragraphs or dialogue in code. Use concise labels.
    - Example: description="dark alley, rain, neon reflections" NOT a full sentence.
    - For brief: use a SHORT summary, not the full creative brief text.

    ## Revision
    - On a QA revision, ``revision_feedback`` is set in context with the failing
      issues (kind, step, message) and recommendations. Adjust the spec
      accordingly instead of replaying the same plan.
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[scene_spec_postcondition],
        max_tokens=8192,
    )))
    async def plan_scene(self, brief: Brief, story_spec: StorySpec | None = None, storyboard_spec: StoryboardSpec | None = None) -> SceneSpec:  # type: ignore[return]
        """Turn the creative brief into a structured scene specification.

        Steps:
        1. Load core skill summaries for context
        2. Analyze brief: extract mood, setting, characters, key actions
        3. If available, use story_spec and storyboard_spec to inform the plan
        4. Load relevant skills (storyboard, cinematography, lighting) as needed
        5. Generate Python code that constructs a SceneSpec with:
           - EnvironmentSpec (description, lighting_mood, rain)
           - CharacterSpec list (name, description, position)
           - ShotSpec list (duration, fps, camera, environment, characters, animation, lighting)
        6. Return the constructed SceneSpec
        """
        self._load_core_skills()

        # Load skills relevant to this brief
        self._load_skills("storyboard", "cinematography", "lighting")

        # Make story and storyboard available in context
        if story_spec:
            self._set_context("story_spec", str(story_spec.to_mapping()))
        if storyboard_spec:
            self._set_context("storyboard_spec", str(storyboard_spec.to_mapping()))

        # The CodeActStrategy will generate Python code to build the SceneSpec
        # Output is validated against SceneSpec type annotation
        ...

    @hidden
    def validate_spec(self, spec: SceneSpec) -> list[str]:
        """Contrôles déterministes d'une SceneSpec (utilisables en tests)."""
        problems: list[str] = []
        if not getattr(spec, "shots", None):
            problems.append("aucun plan")
        return problems
