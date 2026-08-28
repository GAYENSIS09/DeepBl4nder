"""SoundDesignerAgent : conception sonore detaillee (NOOA Agent).

Produit un SoundDesignPlan detaille : foley, ambiances spatiales,
effets sonores, mixage multi-pistes.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin, InvariantError
from DeepBl4nder.domain.media import SoundDesignPlan
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def _sound_design_postcondition(agent: Any, result: Any, call: Any) -> None:
    if not isinstance(result, SoundDesignPlan):
        return
    if not result.layers:
        raise InvariantError(
            "SoundDesignPlan.layers ne doit pas être vide : appelez return_result "
            'avec layers=[{"name": "Ambiance pluie", "layer_type": "ambience"}] '
            "— la liste layers ne doit pas être vide."
        )


class SoundDesignerAgent(BaseAgent, DefaultsMixin):
    """You are a sound design agent for audiovisual productions.

    You create detailed sound design plans with foley, ambiances,
    spatial audio, and multi-track mixing specifications.

    ## Skills available (progressive disclosure)
    - sound-design: foley, ambiances, SFX, spatial audio, mixing
    - cinematography: scene pacing, visual-audio sync
    - music: musical sound design, stingers, transitions

    ## Sound Layers
    - Ambience: background atmosphere (room tone, nature, city)
    - Foley: character movement sounds (footsteps, cloth, props)
    - SFX: specific sound effects (doors, impacts, vehicles)
    - Voice: dialogue processing, reverb, compression
    - Music bed: underscore integration points

    ## Spatial Audio
    - Stereo: basic panning
    - 5.1/7.1: surround positioning
    - Ambisonics: full spherical (for VR/360)

    ## Rules
    - Layer sounds from background to foreground
    - Match reverb to environment size and materials
    - Include timing references for each event
    - Specify frequency ranges to avoid masking
    - Output MUST be a valid SoundDesignPlan
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_sound_design_postcondition],
        max_tokens=8192,
    )))
    async def design_sound(self, scene: SceneSpec) -> SoundDesignPlan:  # type: ignore[return]
        """Design the complete sound landscape for the scene.

        Steps:
        1. Load core skills for context
        2. Analyze scene: environment, characters, actions, weather
        3. Load sound-design and cinematography skills
        4. Design ambient layers (room tone, environment)
        5. Add foley events per character/action
        6. Place SFX cues per shot
        7. Specify spatial positioning
        8. Define mix levels and processing
        9. Return SoundDesignPlan
        """
        self._load_core_skills()
        self._load_skills("sound-design", "cinematography")
        self._set_dynamic("scene_summary", "self._scene_summary()")
        self._scene_data = scene
        ...

    @hidden
    def _scene_summary(self) -> str:
        if not hasattr(self, "_scene_data") or self._scene_data is None:
            return "no scene loaded"
        scene = self._scene_data
        env = scene.environment
        lines = [
            f"Environment: {env.description[:150]}",
            f"Mood: {env.lighting_mood}",
            f"Rain: {env.rain}",
            f"Characters: {[c.name for c in scene.characters]}",
            f"Shots: {len(scene.shots)}",
        ]
        return "\n".join(lines)
