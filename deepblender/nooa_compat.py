"""Compatibilité NOOA : normalisation étendue des appels ``return_result``.

NOOA (≤ 0.0.8) accepte deux formes pour ``return_result`` :

- ``return_result(result=X)`` → clé ``result`` ;
- ``return_result(champ1=..., champ2=...)`` → champs nus, enveloppés
  automatiquement dans ``{"result": {...}}`` (codeact.py:1771-1779).

Les modèles de secours moins disciplinés (ex. llama-3.3 chez NVIDIA,
sollicités quand Gemini/Groq sont indisponibles) produisent parfois une
troisième forme — une enveloppe générique d'appel de fonction :

    {"args": [ {"brief": "...", "environment": {...}, ...} ],
     "function_name": "SceneSpec"}

Passée telle quelle à Pydantic, la validation échoue (« missing: brief » car
les champs sont imbriqués dans ``args[0]``), et les 3 tentatives de correction
de CodeAct répètent la même erreur → ``GenerationError`` → run échoué.

Ce shim déplie ces enveloppes AVANT la validation NOOA, en un seul point :
le patch remplace ``CodeActStrategy._handle_return_result`` (définie une
unique fois dans NOOA, sans surclasse) donc couvre toutes les variantes
(sandbox, Reflexion, futures). Sans effet si les args sont déjà conformes.

Deuxième normalisation au même point d'entrée : réparation des champs
cosmétiques vides mais dérivables (aujourd'hui ``StorySpec.logline``, reconstruit
depuis le synopsis/genre). Sans cela, un modèle de secours produisant une
logline vide épuise ses 3 tentatives sur l'invariant métier et tue le run,
alors que le contenu structurel (acts, dialogues…) est exploitable.

À retirer si une version future de NOOA rend ce point extensible officiellement.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, fields as dc_fields, is_dataclass
from typing import Any

logger = logging.getLogger("DeepBl4nder.pipeline")

# Clé(s) légitimes d'une enveloppe d'appel : on ne déplie que si TOUTES les
# clés présentes y figurent — jamais un payload métier contenant par hasard
# une clé "args".
_ENVELOPE_KEYS = frozenset({"args", "function_name", "name"})

# Découpage grossier en phrases pour extraire une logline du synopsis.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

_LOGLINE_FALLBACK = "Histoire générée sans logline explicite."

# Clés d'une enveloppe tool-call sérialisée en JSON (log 21:34) :
# {"type": "function", "name": "StoryboardSpec", "parameters": {payload}}
_CALL_ENVELOPE_KEYS = frozenset({"type", "name", "function_name", "parameters", "arguments"})

_INSTALLED = False


def _strip_json_fences(text: str) -> str:
    """Retire un encadrement markdown ```json ... ``` éventuel."""
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def parse_json_string_result(args: dict[str, Any]) -> dict[str, Any]:
    """Déplie ``return_result(result='<json>')``.

    Certains modèles de secours sérialisent l'appel d'outil ENTIER en
    chaîne et le passent comme valeur : ``result='{"type": "function",
    "name": "StoryboardSpec", "parameters": {...spec valide...}}'``
    (log 21:34). Pydantic refuse une chaîne pour un dataclass → 3 tentatives
    → run tué, alors que le payload interne est parfaitement formé. On
    parse la chaîne, on extrait le payload (enveloppe tool-call ou champs
    nus) et on remplace la valeur par le dict correspondant — que pydantic
    accepte et coerce profondément.

    Variante du log 22:41 : la même chaîne, mais pretty-printée avec de
    VRAIS sauts de ligne dans les valeurs → ``json.loads`` strict rejette
    (caractères de contrôle). On parse donc en ``strict=False`` et on
    retire d'éventuelles fences markdown.
    """
    if not isinstance(args, dict):
        return args
    value = args.get("result")
    if not isinstance(value, str):
        return args
    text = _strip_json_fences(value.strip())
    if not (text.startswith("{") and text.endswith("}")):
        return args
    try:
        parsed = json.loads(text, strict=False)
    except ValueError:
        return args
    if not isinstance(parsed, dict) or not parsed:
        return args

    keys = set(parsed)
    for key in ("parameters", "arguments"):
        candidate = parsed.get(key)
        if isinstance(candidate, dict) and candidate and keys <= _CALL_ENVELOPE_KEYS:
            logger.info(
                "return_result : result était une chaîne JSON enveloppant un "
                "appel d'outil (%s) → payload extrait.", parsed.get("name", key),
            )
            return {**args, "result": candidate}

    # Chaîne JSON sans enveloppe : payload direct si ce ne sont pas des
    # clés d'enveloppe orphelines (sinon on ne touche pas).
    if not keys <= _CALL_ENVELOPE_KEYS:
        logger.info(
            "return_result : result était une chaîne JSON brute → dict restauré."
        )
        return {**args, "result": parsed}
    return args


def unwrap_return_envelope(args: dict[str, Any]) -> dict[str, Any]:
    """Déplie une enveloppe d'appel non standard vers les champs nus.

    Formes reconnues et dépliées :

    - ``{"args": [payload_dict], "function_name": "X"}`` (et variantes avec
      ``name``, ou sans nom) → ``payload_dict`` ;
    - ``{"arguments": payload_dict}`` / ``{"parameters": payload_dict}``
      (avec optionnellement ``name``/``function_name``) → ``payload_dict``.

    Toute autre structure est retournée inchangée.
    """
    if not isinstance(args, dict) or not args or "result" in args:
        return args
    keys = set(args)

    if keys <= _ENVELOPE_KEYS and isinstance(args.get("args"), list):
        payloads = [item for item in args["args"] if isinstance(item, dict)]
        if len(payloads) == 1 and payloads[0]:
            return payloads[0]

    for key in ("arguments", "parameters"):
        if key in keys and isinstance(args[key], dict):
            extra = keys - {key}
            if extra <= {"name", "function_name"}:
                return args[key]

    return args


# Enveloppe « wrapper typé » sérialisée par NOOA que les modèles faibles
# recopient telle quelle : {"type": "SceneSpec", "value": {...payload...}}
_TYPED_WRAPPER_KEYS = frozenset({"type", "value"})

_UNWRAP_MAX_DEPTH = 10


def _looks_unwrappable(value: Any) -> bool:
    """Le dict courant mérite-t-il qu'on descende d'un niveau ?"""
    if not isinstance(value, dict) or not value:
        return False
    keys = set(value)
    for key in ("parameters", "arguments"):
        candidate = value.get(key)
        if isinstance(candidate, dict) and candidate and keys <= _CALL_ENVELOPE_KEYS:
            return True
    if keys == _TYPED_WRAPPER_KEYS and isinstance(value.get("value"), (dict, list)):
        return True
    # Clé unique enveloppant un dict (ex. log 22:49 : result={"spec": {...}})
    # → descendre. Un payload métier valide n'a jamais cette forme
    # (StorySpec/BlenderScript exigent plusieurs champs), donc aucun risque
    # de casser un payload légitime ; en pire cas la validation échoue
    # pareil qu'avant.
    if len(keys) == 1:
        sole = next(iter(value.values()))
        if isinstance(sole, dict) and sole:
            return True
    return False


def _descend_once(value: dict[str, Any]) -> dict[str, Any]:
    keys = set(value)
    for key in ("parameters", "arguments"):
        candidate = value.get(key)
        if isinstance(candidate, dict) and candidate and keys <= _CALL_ENVELOPE_KEYS:
            return candidate
    if keys == _TYPED_WRAPPER_KEYS and isinstance(value.get("value"), (dict, list)):
        inner = value["value"]
        return inner if isinstance(inner, dict) else {}
    if len(keys) == 1:
        sole = next(iter(value.values()))
        if isinstance(sole, dict) and sole:
            return sole
    return value


def unwrap_typed_wrappers(args: dict[str, Any]) -> dict[str, Any]:
    """Déplie les imbrications ``{"spec": {"type": T, "value": {...}}}``.

    Variante du log 22:49 : même après extraction du payload tool-call,
    llama-3.3 recopie la sérialisation NOOA des arguments — wrapper typé
    ``{"type": ..., "value": ...}`` et/ou clé unique englobante — au lieu
    des champs nus. On descend tant que la structure reste clairement une
    enveloppe ; on s'arrête dès qu'un payload plausible est atteint.
    """
    if not isinstance(args, dict):
        return args
    result = args.get("result")
    if not isinstance(result, dict):
        return args
    current = result
    depth = 0
    while _looks_unwrappable(current) and depth < _UNWRAP_MAX_DEPTH:
        nxt = _descend_once(current)
        if nxt is current:
            break
        current = nxt
        depth += 1
    if current is not result:
        logger.info(
            "return_result : %d niveau(x) d'enveloppe typée déplié(s) "
            "(wrapper NOOA recopié par le modèle).",
            depth,
        )
        return {**args, "result": current}
    return args


def _return_field_names(return_type: Any) -> list[str]:
    """Noms ordonnés des champs du type de retour (dataclass ou pydantic)."""
    if return_type is None or not isinstance(return_type, type):
        return []
    if is_dataclass(return_type):
        return [f.name for f in dc_fields(return_type)]
    model_fields = getattr(return_type, "model_fields", None)
    if isinstance(model_fields, dict):
        return list(model_fields)
    return []


def map_positional_args(args: dict[str, Any], return_type: Any) -> dict[str, Any]:
    """Mappe une enveloppe à arguments POSITIONNELS sur les champs du type.

    Log 23:21 : ``{"args": [True, 0.85, [], []], "function_name": "QAReport"}``
    — le modèle sérialise l'appel comme en Python, avec les valeurs dans
    l'ordre de déclaration. ``unwrap_return_envelope`` n'attrape que la
    forme mono-dict ; ici on zippe les valeurs avec les noms de champs du
    type attendu (connu au point de patch) et on rend des champs nus, que
    NOOA ré-enveloppe lui-même en ``{"result": {...}}``.

    Variante du log 23:52 : arguments EXCÉDENTAIRES (ex. ``'PASS'``, la
    propriété calculée ``status`` recopiée comme un champ). Un appel
    Python valide n'a jamais d'arguments positionnels au-delà des champs
    déclarés → on tronque aux N premiers et on journalise ce qui est
    ignoré.
    """
    if not isinstance(args, dict) or "result" in args:
        return args
    keys = set(args)
    if not keys <= {"args", "function_name", "name"}:
        return args
    values = args.get("args")
    if not isinstance(values, list) or not values:
        return args
    # Forme mono-dict déjà gérée par unwrap_return_envelope.
    if len(values) == 1 and isinstance(values[0], dict):
        return args
    names = _return_field_names(return_type)
    if not names:
        return args
    type_name = getattr(return_type, "__name__", "?")
    if len(values) > len(names):
        dropped = values[len(names):]
        logger.warning(
            "return_result : %d argument(s) positionnel(s) excédentaire(s) "
            "ignoré(s) pour %s : %.200r",
            len(dropped),
            type_name,
            dropped,
        )
        values = values[:len(names)]
    mapped = dict(zip(names, values))
    logger.info(
        "return_result : %d argument(s) positionnel(s) mappé(s) sur les "
        "champs de %s.",
        len(values),
        type_name,
    )
    return mapped


def _derive_logline(payload: dict[str, Any]) -> str | None:
    """Construit une logline acceptable depuis les autres champs du payload.

    Priorité : première phrase du synopsis, sinon « Histoire {genre} {tone} ».
    Retourne ``None`` si rien n'est exploitable (l'invariant métier reprendra
    la main et le modèle devra corriger).
    """
    synopsis = str(payload.get("synopsis") or "").strip()
    if synopsis:
        first = next((s.strip() for s in _SENTENCE_SPLIT.split(synopsis) if s.strip()), "")
        if first:
            return first[:200]
    bits = [b for b in ("Histoire", str(payload.get("genre") or "").strip(),
                        str(payload.get("tone") or "").strip()) if b]
    return " ".join(bits) + "." if len(bits) > 1 else None


def _repair_cosmetic_fields(args: dict[str, Any], return_type: Any) -> None:
    """Complète en place les champs cosmétiques vides mais dérivables.

    Cible actuelle : ``StorySpec.logline``. Les invariants structurels
    (shots, code…) restent stricts : on ne répare QUE ce qui est du
    métadonnée dérivable sans inventer de contenu narratif.
    """
    type_name = getattr(return_type, "__name__", None)
    if type_name != "StorySpec":
        return
    result = args.get("result")
    payload = result if isinstance(result, dict) else args
    if not isinstance(payload, dict):
        return
    if str(payload.get("logline") or "").strip():
        return
    derived = _derive_logline(payload) or _LOGLINE_FALLBACK
    payload["logline"] = derived
    logger.warning(
        "return_result : StorySpec.logline vide → réparée automatiquement "
        "(« %.120s ») ; modèle de secours peu discipliné, qualité à surveiller.",
        derived,
    )


def _plain_item(value: Any) -> dict[str, Any]:
    """dataclass → dict ; dict brut tel quel ; autre → vide (parsers tolérants)."""
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value if isinstance(value, dict) else {}


def _coerce_domain_nesting(result: Any) -> Any:
    """Reconstruit les specs dont les listes imbriquées contiennent des dicts.

    NOOA instancie la dataclass de retour sans conversion récursive : le
    modèle renvoie du JSON et ``shots``/``acts``/``dialogues`` restent des
    listes de dicts bruts. La validation passe (l'invariant ne voit que la
    liste), puis tout consommateur aval plante sur l'accès attribut — ex.
    ``StoryboardSpec.to_mapping`` sur ``s.index`` (log 21:19). On repasse par
    les parsers tolérants du domaine pour livrer de vraies dataclass.
    """
    try:
        from DeepBl4nder.domain.narrative import StoryboardSpec, StorySpec
    except Exception:  # noqa: BLE001 - import jamais bloquant
        return result

    if isinstance(result, StoryboardSpec) and any(
        not is_dataclass(s) for s in result.shots
    ):
        rebuilt = StoryboardSpec.from_mapping(
            {
                "schema_version": result.schema_version,
                "total_duration": result.total_duration,
                "shots": [_plain_item(s) for s in result.shots],
            }
        )
        rebuilt.id = result.id
        logger.info(
            "return_result : shots reçus en dicts bruts → coercition en "
            "StoryboardShot via le parser du domaine."
        )
        return rebuilt

    if isinstance(result, StorySpec) and (
        any(not is_dataclass(a) for a in result.acts)
        or any(not is_dataclass(d) for d in result.dialogues)
    ):
        rebuilt = StorySpec.from_mapping(
            {
                "logline": result.logline,
                "synopsis": result.synopsis,
                "genre": result.genre,
                "tone": result.tone,
                "target_audience": result.target_audience,
                "acts": [_plain_item(a) for a in result.acts],
                "characters": list(result.characters),
                "dialogues": [_plain_item(d) for d in result.dialogues],
                "themes": list(result.themes),
                "schema_version": result.schema_version,
            }
        )
        rebuilt.id = result.id
        logger.info(
            "return_result : acts/dialogues reçus en dicts bruts → coercition "
            "via le parser du domaine."
        )
        return rebuilt

    return result


def install() -> None:
    """Applique le patch (idempotent). Appelé à l'import des agents."""
    global _INSTALLED
    if _INSTALLED:
        return
    from nooa.strategies.codeact import CodeActStrategy

    original = CodeActStrategy._handle_return_result
    if getattr(original, "_DeepBl4nder_unwrap", False):
        _INSTALLED = True
        return

    def patched(
        self: Any,
        runtime: Any,
        tool_call: Any,
        args: dict[str, Any],
        return_type: Any,
        session: Any,
        call: Any,
    ) -> tuple[Any, str | None]:
        normalized = parse_json_string_result(args)
        unwrapped = unwrap_return_envelope(normalized)
        if unwrapped is not normalized:
            logger.info(
                "return_result : enveloppe d'appel non standard dépliée (clés %s)",
                sorted(normalized),
            )
        unwrapped = unwrap_typed_wrappers(unwrapped)
        unwrapped = map_positional_args(unwrapped, return_type)
        _repair_cosmetic_fields(unwrapped, return_type)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "return_result brut : return_type=%s payload=%.800r",
                getattr(return_type, "__name__", return_type),
                unwrapped,
            )
        validated, error_msg = original(
            self, runtime, tool_call, unwrapped, return_type, session, call
        )
        if error_msg is None and validated is not None:
            coerced = _coerce_domain_nesting(validated)
            if coerced is not validated:
                return coerced, None
        return validated, error_msg

    patched._DeepBl4nder_unwrap = True  # type: ignore[attr-defined]
    CodeActStrategy._handle_return_result = patched  # type: ignore[method-assign]
    _patch_reflexion_strategy()
    _INSTALLED = True
    logger.info("nooa_compat : normalisation étendue de return_result active.")


def _patch_reflexion_strategy() -> None:
    """Patch ActorRuntime._prepare_context pour résoudre le bug DynamicContext.

    Bug : ``ReflexionStrategy.get_block_overrides()`` délègue à
    ``self.base.get_block_overrides()`` (CodeActStrategy), qui retourne
    des DynamicContext comme ``strategy.strategy_instructions(runtime)``.
    Mais la variable ``strategy`` dans le namespace d'évaluation est bindée
    à l'instance ``ReflexionStrategy`` (pas au ``CodeActStrategy`` inner),
    et ``ReflexionStrategy`` n'a PAS ces méthodes → AttributeError.

    Fix : Patch ``ActorRuntime._prepare_context`` pour.unwrap le base
    strategy quand le strategy courant est un ``ReflexionStrategy``.
    La variable ``strategy`` dans le namespace d'évaluation pointe alors
    vers le ``CodeActStrategy`` inner, qui possède les méthodes requises.
    """
    try:
        from nooa.runtime.actor import ActorRuntime
        from nooa.strategies.reflexion import ReflexionStrategy
    except ImportError:
        return

    if getattr(ActorRuntime, "_DeepBl4nder_dynamiccontext_fix", False):
        return

    original_prepare_context = ActorRuntime._prepare_context

    async def _patched_prepare_context(
        self: Any,
        method: Any,
        call_args: tuple[Any, ...] = (),
        call_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        # Call original to get the resolved blocks
        blocks = await original_prepare_context(self, method, call_args, call_kwargs)

        # The fix is in the extra_context built by original_prepare_context.
        # We need to intercept BEFORE the blocks are resolved.
        # Since we can't modify the original easily, we re-resolve the
        # DynamicContext blocks that failed.
        # Actually, a simpler approach: patch the strategy BEFORE calling original.

        # Get current strategy
        strategy = getattr(method, "_plan_strategy", None)
        if strategy is None:
            from nooa.runtime.actor import _current_strategy_var
            strategy = _current_strategy_var.get()

        # If it's a ReflexionStrategy, temporarily swap the strategy
        # so the DynamicContext expressions resolve against the base.
        if isinstance(strategy, ReflexionStrategy) and hasattr(strategy, "base"):
            from nooa.runtime.actor import _current_strategy_var
            token = _current_strategy_var.set(strategy.base)
            try:
                blocks = await original_prepare_context(self, method, call_args, call_kwargs)
            finally:
                _current_strategy_var.reset(token)
            return blocks

        return blocks

    ActorRuntime._prepare_context = _patched_prepare_context  # type: ignore[assignment]
    ActorRuntime._DeepBl4nder_dynamiccontext_fix = True  # type: ignore[attr-defined]
    logger.info(
        "nooa_compat : ActorRuntime._prepare_context patché pour DynamicContext "
        "(ReflexionStrategy.base utilisé comme strategy)."
    )
