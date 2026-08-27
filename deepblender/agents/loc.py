"""LocalizationAgent : prépare la localisation d'une production (NOOA Agent).

Produit un `LanguagePackage` typé pour une langue cible (dialogues, sous-titres,
voix, métadonnées). La génération réelle des médias passe par les plugins
subtitle/tts, jamais par l'agent.

Utilise les skills : translation, subtitles, voice.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActStrategy, strategy
from nooa.config import CodeActConfig

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.media import LanguagePackage
from deepblender.domain.scene import SceneSpec
from deepblender.skills.registry import SkillRegistry


def _localization_postcondition(result: LanguagePackage) -> str | None:
    if not result.language:
        return "LanguagePackage.language must be non-empty"
    return None


class LocalizationAgent(BaseAgent, DefaultsMixin):
    """You are a localization agent.

    You prepare a typed localization package for a target language: dialogues,
    subtitles, voice tracks and metadata.

    ## Skills available (progressive disclosure)
    - translation: meaning-preserving translation, cultural adaptation, terminology
    - subtitles: timing, reading speed, line breaking, SDH, formatting (SRT/VTT)
    - voice: casting, direction, lip-sync, emotional range per language

    ## Rules
    - Work from the scene spec and the requested target language.
    - Keep every part typed (LanguagePackage), never raw subtitle files.
    - Preserve meaning over literal translation.
    - Output MUST be a valid LanguagePackage (validated via output_model).
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[_localization_postcondition],
        max_tokens=8192,
    )))
    async def plan_localization(  # type: ignore[return]
        self,
        spec: SceneSpec,
        language: str,
        languages: list[str] | None = None,
    ) -> LanguagePackage:  #type: ignore[return-value]

        """Turn the scene spec into a typed localization package.

        Steps:
        1. Load core skill summaries
        2. Extract dialogues from scene (characters, shots)
        3. Load translation, subtitles, voice skills
        4. Generate LanguagePackage with:
           - language: target language code
           - languages: all languages involved in this lot (target language
             plus the original languages of the characters' lines)
           - dialogues: list of translated lines with character, timing,
             source language and target language
           - subtitles_path: where SRT will be written
           - voice_path: where TTS audio will be written
           - metadata: translation notes, cultural adaptations
           - interface: UI strings for this language

        A character may speak several languages: honor
        ``spec.characters[*].main_language`` and ``spec.characters[*].languages``.
        If ``languages`` is not provided, fall back to ``self.default_languages()``.
        """
        self._load_core_skills()
        self._load_skills("translation", "subtitles", "voice")

        if languages is None:
            languages = self.default_languages()
        self.context["target_languages"] = ", ".join(languages)
        self.context["character_languages"] = ", ".join(sorted({
            lang for char in spec.characters for lang in char.spoken_languages()
        }))

        # NOOA CodeActStrategy generates the return value via LLM at runtime
        ...  