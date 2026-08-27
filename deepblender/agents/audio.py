"""AudioAgent : planifie le son d'une scène (sound design, musique, voix) (NOOA Agent).

Produit un `AudioPlan` typé à partir de la `SceneSpec`. L'agent ne génère pas
d'audio directement : la production effective passe par les plugins audio/TTS
dans un worker dédié (voir DeepBl4nder.plugins).

Utilise les skills : sound-design, music, voice.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin
from DeepBl4nder.domain.media import AudioPlan
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def _audio_postcondition(result: AudioPlan) -> str | None:
    if not result.mood:
        return "AudioPlan.mood must be non-empty"
    return None


class AudioAgent(BaseAgent, DefaultsMixin):
    """You are an audio production agent.

    You turn a typed scene specification into a structured audio plan: sound
    design mood, music theme and tempo, sound effects and voice tracks.

    ## Skills available (progressive disclosure)
    - sound-design: ambience, foley, SFX layering, spatial audio
    - music: themes, leitmotifs, tempo, instrumentation, adaptive scoring
    - voice: casting, direction, recording specs, ADR

    ## Rules
    - Derive the audio mood from the scene lighting and environment.
    - Keep voice tracks and sfx explicit and typed, never free text.
    - Never write raw audio tooling yourself: produce a typed AudioPlan.
    - Output MUST be a valid AudioPlan (validated via output_model).
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_audio_postcondition],
        max_tokens=8192,
    )))
    async def plan_audio(self, spec: SceneSpec) -> AudioPlan:  # type: ignore[return]
        """Turn the scene spec into a structured audio plan.

        Steps:
        1. Load core skill summaries
        2. Analyze scene: environment (rain, indoor/outdoor), lighting mood, shot pacing
        3. Load sound-design, music, voice skills
        4. Generate AudioPlan with:
           - mood, music_theme, tempo
           - volume_music
           - sfx_events: list of (time, description) per shot
           - voice_tracks: list of (character, text, emotion) per shot
        """
        self._load_core_skills()
        self._load_skills("sound-design", "music", "voice")

        ...
