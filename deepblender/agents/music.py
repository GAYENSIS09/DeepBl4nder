"""MusicComposerAgent : compose la musique originale d'une scene (NOOA Agent).

Produit un MusicPlan detaille a partir de la StorySpec et de la SceneSpec :
themes, leitmotivs, orchestrations, tempo, structure musicale.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.agentdoc import hidden
from nooa.config.strategy_config import CodeActConfig

from DeepBl4nder.agents.base import BaseAgent, DefaultsMixin
from DeepBl4nder.domain.media import MusicPlan
from DeepBl4nder.domain.scene import SceneSpec
from DeepBl4nder.skills.registry import SkillRegistry


def _music_postcondition(result: Any) -> str | None:
    if not hasattr(result, "cues") or not result.cues:
        return "MusicPlan must contain at least one music cue"
    return None


class MusicComposerAgent(BaseAgent, DefaultsMixin):
    """You are a music composition agent for audiovisual productions.

    You create original music plans with themes, leitmotifs, orchestrations,
    and adaptive scoring for each scene and emotional beat.

    ## Skills available (progressive disclosure)
    - music: composition, orchestration, leitmotifs, tempo, harmony
    - storytelling: narrative structure, emotional arcs
    - cinematography: scene pacing, emotional beats

    ## Music Structure
    - Theme: main melodic idea (leitmotif per character/idea)
    - Cue: timed music segment tied to scene beats
    - Transition: bridges between cues
    - Stinger: short musical accent for key moments

    ## Instruments (virtual)
    - Orchestra: strings, brass, woodwinds, percussion
    - Electronic: synth pads, bass, leads
    - Hybrid: orchestra + electronic blend
    - Minimal: piano, solo instrument

    ## Rules
    - Derive tempo from scene pacing (fast action = fast tempo)
    - Match key/mood to lighting and environment
    - Include silence cues for dramatic pauses
    - Mark adaptive points for interactive re-scoring
    - Output MUST be a valid MusicPlan
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_music_postcondition],
        max_tokens=8192,
    )))
    async def compose_music(self, scene: SceneSpec) -> MusicPlan:  # type: ignore[return]
        """Compose original music for the scene.

        Steps:
        1. Load core skills for context
        2. Analyze scene: mood, pacing, characters, emotional arc
        3. Load music and storytelling skills
        4. Design main theme (leitmotif)
        5. Create timed cues for each shot/beat
        6. Specify instruments, tempo, key per cue
        7. Add transition and stinger cues
        8. Return MusicPlan
        """
        self._load_core_skills()
        self._load_skills("music", "storytelling", "cinematography")
        self._set_dynamic("scene_summary", "self._scene_summary()")
        self._scene_data = scene
        ...

    @hidden
    def _scene_summary(self) -> str:
        if not hasattr(self, "_scene_data") or self._scene_data is None:
            return "no scene loaded"
        scene = self._scene_data
        env = scene.environment
        total_dur = sum(s.duration for s in scene.shots) if scene.shots else 0
        lines = [
            f"Brief: {scene.brief[:150]}",
            f"Mood: {env.lighting_mood}",
            f"Duration: {total_dur:.1f}s",
            f"Shots: {len(scene.shots)}",
            f"Characters: {[c.name for c in scene.characters]}",
        ]
        return "\n".join(lines)
