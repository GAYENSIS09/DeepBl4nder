"""BaseAgent : classe de base pour tous les agents DeepBlender (NOOA).

Factorise le chargement de skills, la configuration NOOA et les patterns communs.

Exploite NOOA 0.0.8 (00-nooa.md) :
- ``TruncationConfig`` : budget de contexte / événements (env ``DEEPBLENDER_AGENT_TRUNCATION``).
- ``SQLiteStorageManager`` : persistance d'état de l'agent (env ``DEEPBLENDER_AGENT_STORAGE``).
- ``nooa.tracing`` : observabilité des boucles agentiques (env ``DEEPBLENDER_TRACING``).
- ``@hidden`` (agentdoc) : masque les helpers internes du rendu modèle.
- postconditions : invariants métier (``InvariantError`` -> retry de validation modèle).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nooa import Agent, CodeActStrategy, Context, EventQuery, strategy
from nooa.agentdoc import hidden
from nooa.skill import TextSkill
from nooa.strategy_validation import InvariantError

from deepblender.skills.registry import SkillRegistry, get_default_registry

_TRACING_ENABLED = False
_SENTINEL = object()


def _sandbox_enabled() -> bool:
    """True si ``DEEPBLENDER_SANDBOX=1`` : exécution de code dans un worker confiné."""
    return os.getenv("DEEPBLENDER_SANDBOX", "").lower() in ("1", "true", "yes", "on")


def _default_memory_skill() -> Any:
    """MemorySkill (nooa-memory) si l'extra est installé, sinon None."""
    try:
        from nooa_memory.memory_skill import MemorySkill

        return MemorySkill()
    except Exception:  # noqa: BLE001 - extra indisponible => pas de mémoire
        return None


def _default_event_query() -> Any:
    """EventQuery depuis ``DEEPBLENDER_EVENT_QUERY=<type>`` (None = défaut NOOA)."""
    etype = os.getenv("DEEPBLENDER_EVENT_QUERY", "").strip()
    if not etype:
        return None
    return EventQuery(type=etype, limit=8)


def _default_truncation() -> Any:
    """TruncationConfig depuis l'environnement (None = comportement NOOA par défaut).

    ``DEEPBLENDER_AGENT_TRUNCATION=1`` active ; ``LLM_CONTEXT_TOKENS`` et
    ``LLM_EVENT_TOKENS`` fixent les budgets (défauts raisonnables sinon).
    """
    if os.getenv("DEEPBLENDER_AGENT_TRUNCATION", "").lower() not in ("1", "true", "yes", "on"):
        return None
    try:
        from nooa.config.truncation_config import TruncationConfig

        def _int(name: str) -> int | None:
            raw = os.getenv(name, "").strip()
            return int(raw) if raw else None

        return TruncationConfig(
            max_context_tokens=_int("LLM_CONTEXT_TOKENS") or 64_000,
            max_event_tokens=_int("LLM_EVENT_TOKENS"),
            min_preserved_events=8,
            response_reserve_tokens=2_048,
        )
    except Exception:  # noqa: BLE001 - config invalide => défaut NOOA
        return None


def _default_storage() -> Any:
    """SQLiteStorageManager si ``DEEPBLENDER_AGENT_STORAGE=<chemin db>`` est défini."""
    path = os.getenv("DEEPBLENDER_AGENT_STORAGE", "").strip()
    if not path:
        return None
    try:
        from nooa.storage import SQLiteStorageManager

        return SQLiteStorageManager(Path(path))
    except Exception:  # noqa: BLE001 - stockage indisponible => None
        return None


def _enable_tracing_if_configured() -> None:
    """Active le tracing NOOA une fois, si ``DEEPBLENDER_TRACING`` est défini."""
    global _TRACING_ENABLED
    if _TRACING_ENABLED:
        return
    if os.getenv("DEEPBLENDER_TRACING", "").lower() not in ("1", "true", "yes", "on"):
        return
    try:
        import nooa.tracing as tracing

        tracing.enable_tracing()
    except Exception:  # noqa: BLE001 - tracing indisponible, jamais bloquant
        pass
    finally:
        _TRACING_ENABLED = True


def scene_spec_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : une SceneSpec planifiée doit contenir au moins un plan.

    Lève ``InvariantError`` (retry de validation NOOA, modèle corrigeable)
    plutôt que de laisser passer une spec vide.
    """
    from deepblender.domain.scene import SceneSpec

    if not isinstance(result, SceneSpec):
        return
    if not getattr(result, "shots", None):
        raise InvariantError("SceneSpec doit contenir au moins un plan (shots non vide).")


def blender_script_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : un BlenderScript généré doit avoir du code non vide."""
    from deepblender.domain.scene import BlenderScript

    if not isinstance(result, BlenderScript):
        return
    if not (result.code or "").strip():
        raise InvariantError("BlenderScript.code ne doit pas être vide.")


def codeact_with_sandbox(config: Any = None) -> CodeActStrategy:
    """CodeActStrategy avec backend sandbox quand ``DEEPBLENDER_SANDBOX=1``."""
    from nooa.config.strategy_config import CodeActConfig

    base = config or CodeActConfig()
    if _sandbox_enabled() and getattr(base, "execution_backend", "inprocess") == "inprocess":
        base = base.model_copy(update={"execution_backend": "sandbox"})
    return CodeActStrategy(config=base)


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
        truncation: Any = None,
        storage: Any = None,
        memory: Any = _SENTINEL,
        **kwargs: Any,
    ) -> None:
        self._skill_registry = skill_registry or get_default_registry()
        _enable_tracing_if_configured()
        if truncation is None:
            truncation = _default_truncation()
        if storage is None:
            storage = _default_storage()
        self._storage = storage
        self._memory_skill: Any = None
        if truncation is not None:
            kwargs.setdefault("truncation", truncation)
        if storage is not None:
            kwargs.setdefault("storage", storage)
        event_query = _default_event_query()
        if event_query is not None:
            kwargs.setdefault("event_query", event_query)
        super().__init__(*args, **kwargs)
        self._enable_memory(memory)

    @hidden
    def _enable_memory(self, memory: Any = _SENTINEL) -> bool:
        """Attache la mémoire long terme (nooa-memory) si demandée.

        ``memory=True`` ou ``DEEPBLENDER_AGENT_MEMORY=1`` active la mémoire ;
        la gestion écrit dans ``MEMORY_STORAGE_PATH`` (fourni par l'environnement).
        """
        if memory is _SENTINEL:
            memory = os.getenv("DEEPBLENDER_AGENT_MEMORY", "").lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
        if not memory or self._memory_skill is not None:
            return self._memory_skill is not None
        skill = _default_memory_skill()
        if skill is None:
            return False
        try:
            skill.attach(self)
        except Exception:  # noqa: BLE001 - la mémoire ne doit jamais bloquer
            return False
        self._memory_skill = skill
        return True

    @hidden
    def _set_dynamic(self, key: str, expr: str) -> None:
        """Contexte dynamique : expression réévaluée au début de chaque tour LLM."""
        self.context[key] = Context(expr=expr)

    def memory_skill(self) -> Any:
        """Skill mémoire attaché (nooa-memory) ou None."""
        return self._memory_skill

    @property
    def memory(self) -> Any:
        """MemoryManager NOOA (installé par MemorySkill) ou None."""
        return getattr(self, "_memory", None)

    @hidden
    def _load_core_skills(self) -> None:
        """Injecte les résumés de tous les skills dans le contexte (niveau 1).

        Idempotent : ne recharge pas si déjà fait.
        """
        if self._core_skills_loaded:
            return
        summaries = self._skill_registry.summaries()
        self.context.set("available_skills", "\n".join(summaries))
        self._core_skills_loaded = True

    @hidden
    def _load_skill(self, name: str) -> TextSkill:
        """Charge un skill complet dans le contexte (niveau 2+)."""
        skill = self._skill_registry.resolve(name)
        self.context.set(f"skill_{name}", skill.__doc__ or "")
        return skill

    @hidden
    def _load_skills(self, *names: str) -> list[TextSkill]:
        """Charge plusieurs skills d'un coup."""
        return [self._load_skill(name) for name in names]

    @strategy(CodeActStrategy())
    @hidden
    async def _codeact(self, *args: Any, **kwargs: Any) -> Any:
        """Point d'entrée CodeActStrategy - à surcharger dans les sous-classes."""
        ...

    def get_skill_registry(self) -> SkillRegistry:
        """Accès au registre pour tests ou configuration avancée."""
        return self._skill_registry

    def _get_model_id(self) -> str:
        """Retourne l'identifiant du modèle LLM utilisé."""
        try:
            from deepblender.llm import model_from_env
            return model_from_env()
        except Exception:
            return "unknown"


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

    def default_languages(self) -> list[str]:
        """Langues cibles par défaut (support multilingue)."""
        return ["fr"]

    def default_language(self) -> str:
        """Langue principale par défaut (première langue cible)."""
        return self.default_languages()[0]

    def frame_count(self, duration: float, fps: int | None = None) -> int:
        """Nombre de frames déterministes."""
        return round(duration * (fps or self.default_fps()))
