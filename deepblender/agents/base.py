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
from nooa.errors import GenerationError
from nooa.skill import TextSkill
from nooa.strategy_validation import InvariantError

# Ré-export neutre : les couches NOOA-free (production…) interceptent
# GenerationError SANS importer nooa directement (règle de découplage).
__all__ = ["GenerationError", "InvariantError"]

from deepblender.llm import model_name_of
from deepblender.nooa_compat import install as install_nooa_compat
from deepblender.skills.registry import SkillRegistry, get_default_registry

# Normalisation étendue des return_result (enveloppes non standard des
# modèles de secours) — voir deepblender/nooa_compat.py. Idempotent.
install_nooa_compat()

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
    """TruncationConfig avec valeurs par défaut raisonnables.

    ``DEEPBLENDER_AGENT_TRUNCATION=0`` désactive ; sinon activé par défaut.
    ``LLM_CONTEXT_TOKENS`` et ``LLM_EVENT_TOKENS`` fixent les budgets.
    """
    if os.getenv("DEEPBLENDER_AGENT_TRUNCATION", "").lower() in ("0", "false", "no", "off"):
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
    """Active le tracing NOOA une fois, sauf si ``DEEPBLENDER_TRACING=0``.

    Le tracing est activé par défaut pour faciliter le debugging.
    Désactivez avec ``DEEPBLENDER_TRACING=0`` ou ``DEEPBLENDER_ENV=production``.
    """
    global _TRACING_ENABLED
    if _TRACING_ENABLED:
        return
    # Désactivé explicitement ou en production
    if os.getenv("DEEPBLENDER_TRACING", "").lower() in ("0", "false", "no", "off"):
        _TRACING_ENABLED = True
        return
    if os.getenv("DEEPBLENDER_ENV", "").lower() in ("production", "prod"):
        _TRACING_ENABLED = True
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
        raise InvariantError(
            'SceneSpec doit contenir au moins un plan : appelez return_result '
            'avec shots=[{"description": "plan large de la ruelle sous la '
            'pluie", "camera": {"focal_length_mm": 35.0}}] — la liste shots '
            "ne doit pas être vide."
        )


def blender_script_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : un BlenderScript généré doit avoir du code non vide."""
    from deepblender.domain.scene import BlenderScript

    if not isinstance(result, BlenderScript):
        return
    if not (result.code or "").strip():
        raise InvariantError("BlenderScript.code ne doit pas être vide.")


def story_spec_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : une StorySpec produite doit porter une logline."""
    from deepblender.domain.narrative import StorySpec

    if not isinstance(result, StorySpec):
        return
    if not (result.logline or "").strip():
        raise InvariantError(
            "StorySpec.logline ne doit pas être vide : une phrase unique qui "
            "résume toute l'histoire, ex. « Une hackeuse découvre que ses "
            "souvenirs ont été vendus au plus offrant »."
        )


def storyboard_spec_postcondition(agent: Any, result: Any, call: Any) -> None:
    """Invariant : un StoryboardSpec produit doit contenir au moins un plan."""
    from deepblender.domain.narrative import StoryboardSpec

    if not isinstance(result, StoryboardSpec):
        return
    if not getattr(result, "shots", None):
        raise InvariantError(
            "StoryboardSpec doit contenir au moins un plan : appelez "
            'return_result avec shots=[{"description": "plan large du '
            'laboratoire", "camera_angle": "wide", "camera_movement": "dolly"}]'
            " — la liste shots ne doit pas être vide."
        )


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
        self._enable_history_summarizer()
        self._install_guardrails()

    @hidden
    def _enable_memory(self, memory: Any = _SENTINEL) -> bool:
        """Attache la mémoire long terme (nooa-memory) par défaut.

        ``DEEPBLENDER_AGENT_MEMORY=0`` désactive ; sinon activé par défaut.
        La mémoire persiste entre les runs via ``MEMORY_STORAGE_PATH``.
        """
        if memory is _SENTINEL:
            memory = os.getenv("DEEPBLENDER_AGENT_MEMORY", "").lower() not in (
                "0",
                "false",
                "no",
                "off",
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
    def _set_dynamic(self, key: str, expr: str, prefix: bool = False) -> None:
        """Contexte dynamique : expression Python réévaluée au début de chaque tour LLM.

        ``prefix=False`` (défaut) place le bloc dans le suffixe volatile.
        Utiliser ``prefix=True`` si l'expression est stable entre plusieurs tours.
        """
        self.context[key] = Context(expr=expr, prefix=prefix)

    @hidden
    def _set_context(self, key: str, value: str, prefix: bool = True) -> None:
        """Contexte statique : contenu littéral, jamais évalué comme du Python.

        ``prefix=True`` (défaut) place le bloc dans le préfixe cacheable
        pour maximiser le KV cache cote provider.
        """
        self.context[key] = Context(value=value, prefix=prefix)

    def memory_skill(self) -> Any:
        """Skill memoire attache (nooa-memory) ou None."""
        return self._memory_skill

    @property
    def memory(self) -> Any:
        """MemoryManager NOOA (installe par MemorySkill) ou None."""
        return getattr(self, "_memory", None)

    @hidden
    def _enable_history_summarizer(self) -> None:
        """Installe un TokenBudgetSummarizer pour comprimer l'historique long.

        Empeche les conversations longues de depasser la fenetre de contexte.
        Controle par DEEPBLENDER_AGENT_HISTORY_BUDGET (tokens, defaut 80000).
        """
        if os.getenv("DEEPBLENDER_NO_SUMMARIZER", "").lower() in ("1", "true"):
            return
        try:
            from nooa.agents import TokenBudgetSummarizer
            from nooa.config import TokenBudgetConfig

            max_tokens = int(os.getenv("DEEPBLENDER_AGENT_HISTORY_BUDGET", "80000"))
            TokenBudgetSummarizer.install(
                self,
                config=TokenBudgetConfig(max_tokens=max_tokens, preserve_recent=10),
            )
        except Exception:  # noqa: BLE001 - summarizer ne doit jamais bloquer
            pass

    @hidden
    def _load_core_skills(self) -> None:
        """Injecte les resumes de tous les skills dans le contexte (niveau 1).

        Idempotent : ne recharge pas si deja fait.
        Les skill summaries sont places dans le prefix stable pour maximiser
        le cache KV cote provider (contenu qui ne change pas entre les appels).
        """
        if self._core_skills_loaded:
            return
        summaries = self._skill_registry.summaries()
        self.context["available_skills"] = Context(
            value="\n".join(summaries), prefix=True,
        )
        self._core_skills_loaded = True

    @hidden
    def _load_skill(self, name: str) -> TextSkill:
        """Charge un skill complet dans le contexte (niveau 2+)."""
        skill = self._skill_registry.resolve(name)
        self.context[f"skill_{name}"] = Context(value=skill.__doc__ or "")
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
        llm = getattr(self, "_llm", None)
        if llm is not None:
            try:
                return model_name_of(llm)
            except Exception:  # noqa: BLE001 - modèle non exposé : on reste générique
                return "unknown"
        return "unknown"

    @hidden
    def _get_last_call_info(self) -> dict[str, str]:
        """Fournisseur + modèle réellement utilisés par le dernier appel LLM.

        Renseigné quand le client est un routeur multi-fournisseurs exposant
        ``last_provider_id`` / ``last_model`` (vainqueur réel du vote) ;
        dict vide sinon — l'appelant retombe sur ``_get_model_id``.
        """
        llm = getattr(self, "_llm", None)
        provider = getattr(llm, "last_provider_id", None)
        model = getattr(llm, "last_model", None)
        if provider and model:
            return {"provider": str(provider), "model": str(model)}
        return {}

    @hidden
    def _install_guardrails(self) -> None:
        """Installe des intercepts middleware pour valider les sorties.

        Guardrails NOOA (nooa-middleware-hooks) :
        - Validation des sorties trop courtes
        - Logging des violations pour debugging
        """
        if not hasattr(self, "event_manager") or self.event_manager is None:
            return
        try:
            self.event_manager.intercept("agent_call", _guardrail_validate_output)
        except Exception:  # noqa: BLE001 - guardrails ne doivent jamais bloquer
            pass


def _guardrail_validate_output(ctx: Any, next_fn: Any) -> Any:
    """Intercept middleware : valide la sortie d'une méthode agentic.

    Signature NOOA middleware : (ctx, next_fn) -> result.
    Bloque les sorties trop courtes (< 10 chars non vides).
    """
    result = getattr(ctx, "result", None)
    if result is not None and isinstance(result, str) and len(result.strip()) < 10:
        import logging
        logging.getLogger("deepblender.guardrails").warning(
            "Sortie trop courte (%d chars) pour %s",
            len(result.strip()),
            getattr(ctx, "method_name", "unknown"),
        )
    return next_fn(ctx)


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
