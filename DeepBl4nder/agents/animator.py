"""AnimatorAgent : anime les personnages 3D (NOOA Agent).

Génère des clips d'animation (keyframes, contraintes, lip sync)
pour chaque plan de la scène.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, InvariantError
from DeepBl4nder.domain.media import AnimationResult
from DeepBl4nder.domain.scene import SceneSpec, ShotSpec
from DeepBl4nder.skills.registry import SkillRegistry


def _animation_postcondition(agent: Any, result: Any, call: Any) -> None:
    if not isinstance(result, AnimationResult):
        return
    if not result.clips:
        raise InvariantError(
            "AnimationResult.clips ne doit pas être vide : appelez return_result "
            'avec clips=[{"character_name": "Héros", "shot_index": 0, '
            '"keyframes": [], "duration": 4.0}] — la liste clips ne doit pas '
            "être vide."
        )


class AnimatorAgent(BaseAgent, DefaultsMixin):
    """You are a character animation agent for 3D scenes.

    You generate animation clips for each character in each shot,
    including keyframes, constraints, lip sync, and facial expressions.

    ## Skills available (progressive disclosure)
    - animation: keyframes, fcurves, drivers, NLA
    - character-design: character proportions, poses
    - rigging: armatures, bones, constraints
    - camera: camera movement for shot context

    ## Animation Types
    - Idle: subtle breathing, weight shift
    - Walk/Run: cyclical locomotion
    - Gesture: hand/arm movements
    - Dialogue: lip sync + facial expressions
    - Action: combat, interaction, dynamic movement
    - Camera-relative: animation that works with camera angle

    ## Rules
    - Match animation to shot duration and FPS
    - Use interpolation appropriate to the action type
    - Include hold frames at start/end for smooth transitions
    - Mark lip_sync=True for dialogue shots
    - Keep keyframe count reasonable (performance)
    - Output MUST be a valid AnimationResult
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_animation_postcondition],
        max_tokens=8192,
    )))
    async def generate_animations(self, scene: SceneSpec) -> AnimationResult:  # type: ignore[return]
        """Generate animation clips for all characters in all shots.

        Steps:
        1. Load core skills for context
        2. Analyze SceneSpec: characters, shots, animation descriptions
        3. Load animation and rigging skills
        4. For each shot, for each character:
           - Determine animation type from shot description
           - Generate keyframes for location, rotation, scale
           - Add constraints (Track To, IK, etc.) if needed
           - Add lip sync if dialogue shot
           - Add facial expression keyframes
        5. Return AnimationResult with all clips
        """
        self._load_core_skills()
        self._load_skills("animation", "character-design", "rigging")
        self._set_dynamic("scene_summary", "self._scene_summary()")
        self._scene_data = scene
        ...

    @hidden
    def _scene_summary(self) -> str:
        if not hasattr(self, "_scene_data") or self._scene_data is None:
            return "no scene loaded"
        scene = self._scene_data
        lines = []
        for i, shot in enumerate(scene.shots):
            chars = ", ".join(shot.characters) if shot.characters else "none"
            anim = getattr(shot, "animation", "") or "none"
            lines.append(f"Shot {i}: {shot.duration}s, chars=[{chars}], anim={anim[:50]}")
        return f"Shots: {len(scene.shots)}\n" + "\n".join(lines)
