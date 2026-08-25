"""AnimatorAgent : anime les personnages 3D (NOOA Agent).

Génère des clips d'animation (keyframes, contraintes, lip sync)
pour chaque plan de la scène.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.scene import SceneSpec, ShotSpec
from deepblender.skills.registry import SkillRegistry


def _animation_postcondition(result: Any) -> str | None:
    if not hasattr(result, "clips") or not result.clips:
        return "AnimationResult must contain at least one animation clip"
    return None


class AnimationClip:
    """Un clip d'animation pour un personnage dans un plan."""

    def __init__(
        self,
        character_name: str,
        shot_index: int,
        keyframes: list[Keyframe] | None = None,
        constraints: list[Constraint] | None = None,
        lip_sync: bool = False,
        expression: str | None = None,
        duration: float = 0.0,
        fps: int = 24,
    ) -> None:
        self.character_name = character_name
        self.shot_index = shot_index
        self.keyframes = keyframes or []
        self.constraints = constraints or []
        self.lip_sync = lip_sync
        self.expression = expression
        self.duration = duration
        self.fps = fps

    def to_mapping(self) -> dict[str, Any]:
        return {
            "character_name": self.character_name,
            "shot_index": self.shot_index,
            "keyframes": [k.to_mapping() for k in self.keyframes],
            "constraints": [c.to_mapping() for c in self.constraints],
            "lip_sync": self.lip_sync,
            "expression": self.expression,
            "duration": self.duration,
            "fps": self.fps,
        }


class Keyframe:
    """Un keyframe d'animation."""

    def __init__(
        self,
        frame: int,
        property_path: str,
        value: Any,
        interpolation: str = "BEZIER",
    ) -> None:
        self.frame = frame
        self.property_path = property_path
        self.value = value
        self.interpolation = interpolation

    def to_mapping(self) -> dict[str, Any]:
        return {
            "frame": self.frame,
            "property_path": self.property_path,
            "value": self.value,
            "interpolation": self.interpolation,
        }


class Constraint:
    """Une contrainte d'animation."""

    def __init__(
        self,
        type: str,
        target: str | None = None,
        influence: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> None:
        self.type = type
        self.target = target
        self.influence = influence
        self.properties = properties or {}

    def to_mapping(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "target": self.target,
            "influence": self.influence,
            "properties": self.properties,
        }


class AnimationResult:
    """Résultat de la génération d'animations."""

    def __init__(self, clips: list[AnimationClip]) -> None:
        self.clips = clips

    def to_mapping(self) -> dict[str, Any]:
        return {"clips": [c.to_mapping() for c in self.clips]}


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
