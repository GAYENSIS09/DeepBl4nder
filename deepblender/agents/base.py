"""BaseAgent : classe de base pour tous les agents DeepBlender (NOOA).

Factorise le chargement de skills, la configuration NOOA et les patterns communs.
"""

from __future__ import annotations

from typing import Any

from nooa import Agent, CodeActStrategy, strategy
from nooa.skill import TextSkill

from deepblender.skills.registry import SkillRegistry, get_default_registry


class BaseAgent(Agent):
    """Classe de base pour agents DeepBlender avec progressive disclosure des skills.

    Fournit :
    - Registre de skills partagé (injecté ou défaut singleton)
    - _load_core_skills() : injecte les résumés (niveau 1)
    - _load_skill(name) : charge le skill complet (niveau 2+)
    - Stratégie CodeActStrategy par défaut
    """

    _skill_registry: SkillRegistry
    _core_skills_loaded: bool = False

    def __init__(
        self,
        *args: Any,
        skill_registry: SkillRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        self._skill_registry = skill_registry or get_default_registry()
        super().__init__(*args, **kwargs)

    def _load_core_skills(self) -> None:
        """Injecte les résumés de tous les skills dans le contexte (niveau 1).

        Idempotent : ne recharge pas si déjà fait.
        """
        if self._core_skills_loaded:
            return
        summaries = self._skill_registry.summaries()
        self.context.set("available_skills", "\n".join(summaries))
        self._core_skills_loaded = True

    def _load_skill(self, name: str) -> TextSkill:
        """Charge un skill complet dans le contexte (niveau 2+)."""
        skill = self._skill_registry.resolve(name)
        self.context.set(f"skill_{name}", skill.__doc__ or "")
        return skill

    def _load_skills(self, *names: str) -> list[TextSkill]:
        """Charge plusieurs skills d'un coup."""
        return [self._load_skill(name) for name in names]

    @strategy(CodeActStrategy())
    async def _codeact(self, *args: Any, **kwargs: Any) -> Any:
        """Point d'entrée CodeActStrategy - à surcharger dans les sous-classes."""
        ...

    def get_skill_registry(self) -> SkillRegistry:
        """Accès au registre pour tests ou configuration avancée."""
        return self._skill_registry


class DefaultsMixin:
    """Mixin pour méthodes déterministes par défaut (P3 - corps Python).

    Les sous-classes peuvent surcharger ces méthodes pour configurer
    des valeurs par défaut sans LLM.
    """

    def default_shot_duration(self) -> float:
        """Durée par défaut d'un plan (secondes)."""
        return 5.0

    def default_fps(self) -> int:
        """FPS par défaut."""
        return 24

    def default_music_volume(self) -> float:
        """Volume musique par défaut (gain linéaire 0..1)."""
        return 0.4

    def default_output_format(self) -> str:
        """Format de sortie compositing par défaut."""
        return "exr"

    def default_language(self) -> str:
        """Langue cible par défaut."""
        return "fr"

    def frame_count(self, duration: float, fps: int | None = None) -> int:
        """Nombre de frames déterministes."""
        return round(duration * (fps or self.default_fps()))