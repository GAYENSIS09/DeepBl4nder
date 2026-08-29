"""AIVideoAgent : transforme une SceneSpec en commandes de génération vidéo par IA (NOOA Agent).

Le AIVideoAgent génère une séquence de commandes de génération qui, exécutées
sur le serveur AI Video, créent des vidéos à partir de prompts textuels ou d'images.

Utilise le skill : ai-video.
"""

from __future__ import annotations

from typing import Any

from nooa import strategy
from nooa.agentdoc import hidden, pformat
from nooa.config.strategy_config import CodeActConfig
from nooa.strategy_validation import InvariantError

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, codeact_with_sandbox
from DeepBl4nder.domain.ai_video import AIVideoCommand, AIVideoCommands
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def ai_video_commands_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : AIVideoCommands doit contenir au moins une commande."""
    if not isinstance(result, AIVideoCommands):
        return
    if not result.commands:
        raise InvariantError(
            "AIVideoCommands doit contenir au moins une commande de génération. "
            "Ajoutez generate/t2v ou generate/i2v."
        )


class AIVideoAgent(BaseAgent, DefaultsMixin):
    """You are an AI Video generation pipeline agent.

    You transform a typed SceneSpec into a sequence of generation commands that,
    sent to an AI Video server, create video clips using diffusion models.

    ## Skills available
    - ai-video: CogVideoX, Wan2.1, AnimateDiff, SVD, LTX, Mochi

    ## Rules
    - Generate deterministic command sequences (fixed seed).
    - Use the appropriate model for each use case.
    - Commands must be valid REST endpoints for the AI Video server.
    - Output MUST be valid AIVideoCommands (validated via postcondition).
    - Always set seed for reproducibility.
    - Use cache to avoid redundant generation costs.

    ## Command sequence
    The commands must follow this order:
    1. generate/t2v or generate/i2v — generate video clips
    2. Each clip should be 4-8 seconds (AI Video limitation)

    ## Model selection
    | Use Case              | Model       | Mode | Why                              |
    |-----------------------|-------------|------|----------------------------------|
    | Previz (rough draft)  | AnimateDiff | T2V  | Fast, low VRAM (8GB)             |
    | Realistic scenes      | CogVideoX   | T2V  | High quality, realistic output   |
    | Long animations       | Wan2.1      | T2V  | Very high quality, 24GB+ VRAM    |
    | Animate from image    | SVD         | I2V  | Best for image animation         |
    | Video + audio         | LTX-2.5     | T2V  | Combined video and audio         |
    | High realism          | Mochi 1     | T2V  | Best motion realism              |

    ## AI Video vs Blender
    | Use Case              | AI Video | Blender |
    |-----------------------|----------|---------|
    | Previz (rough draft)  | ✅       | ⚠️      |
    | Special effects       | ✅       | ⚠️      |
    | Transitions           | ✅       | ❌      |
    | Social media clips    | ✅       | ❌      |
    | Final render          | ❌       | ✅      |
    | Detailed characters   | ❌       | ✅      |

    ## Integration with Blender
    - AI Video generates previz or effects
    - Blender handles final render
    - Use FFmpeg to merge AI clips with Blender renders
    - Cache AI generations to avoid redundant costs

    ## Limitations
    - Max duration: 4-8 seconds per clip
    - Temporal inconsistency: use fixed seeds
    - No camera control: use Blender for camera, AI for details
    - Variable quality: multi-pass workflow
    - High GPU cost: cache generations, use previz mode

    ## Units
    - AI Video has no spatial units (2D generation)
    - Use prompts to describe spatial relationships
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
        postconditions=[ai_video_commands_postcondition],
        max_tokens=16384,
    )))
    async def build_commands(self, spec: SceneSpec) -> AIVideoCommands:  # type: ignore[return]
        """Turn the scene spec into AI Video generation commands.

        Steps:
        1. Load ai-video skill
        2. Analyze SceneSpec: environment, shots, animation
        3. Determine which shots need AI Video vs Blender
        4. Generate prompts for each AI Video shot
        5. Select appropriate model based on use case
        6. Generate REST commands:
           - generate/t2v for text-to-video clips
           - generate/i2v for image-to-video animation
        7. Return AIVideoCommands
        """
        self._load_core_skills()
        self._load_skill("ai-video")

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
            "engine": "AI_VIDEO",
            "resolution": spec.render.resolution,
            "fps": spec.render.fps,
        }
        return pformat(summary)

    def _ai_video_model_for_mood(self, mood: str) -> str:
        """Sélectionne le modèle AI Video approprié selon l'humeur."""
        model_map = {
            "neutral": "cogvideox",
            "warm": "cogvideox",
            "cold": "cogvideox",
            "dramatic": "cogvideox",
            "cinematic": "cogvideox",
        }
        return model_map.get(mood, "cogvideox")

    def _ai_video_prompt_from_spec(self, spec: SceneSpec, shot_index: int) -> str:
        """Génère un prompt textuel à partir de la SceneSpec pour un plan donné."""
        env = spec.environment
        shot = spec.shots[shot_index] if shot_index < len(spec.shots) else None

        parts = []
        if env.description:
            parts.append(env.description)
        if shot and shot.animation.description:
            parts.append(shot.animation.description)
        if spec.characters:
            char_descs = [c.description for c in spec.characters if c.description]
            if char_descs:
                parts.append("featuring " + ", ".join(char_descs[:3]))

        return ". ".join(parts) if parts else spec.brief
