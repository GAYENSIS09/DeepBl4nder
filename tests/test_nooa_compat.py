"""Compat NOOA : dépliage des enveloppes return_result non standard.

Régression : NVIDIA llama-3.3 (modèle de secours) appelait
``return_result(args=[{...SceneSpec...}], function_name="SceneSpec")``
→ validation Pydantic échouée 3 fois → GenerationError → run échoué.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from deepblender.nooa_compat import (
    install,
    parse_json_string_result,
    unwrap_return_envelope,
    unwrap_typed_wrappers,
)
from deepblender.domain.narrative import StorySpec, StoryboardShot, StoryboardSpec
from deepblender.domain.qa import QAReport
from deepblender.domain.scene import BlenderScript


class TinySpec(BaseModel):
    brief: str
    shots: list[str]


def test_unwrap_function_call_envelope() -> None:
    """La forme exacte du log : {'args': [payload], 'function_name': X}."""
    payload = {"brief": "Cyberpunk alley", "shots": ["s1"]}
    args = {"args": [payload], "function_name": "TinySpec"}
    assert unwrap_return_envelope(args) == payload


def test_unwrap_arguments_and_parameters_envelopes() -> None:
    payload = {"brief": "b", "shots": []}
    assert unwrap_return_envelope({"arguments": payload}) == payload
    assert unwrap_return_envelope({"parameters": payload, "name": "x"}) == payload


@pytest.mark.parametrize(
    "args",
    [
        {"result": {"brief": "b", "shots": []}},  # forme canonique → intacte
        {"brief": "b", "shots": []},  # champs nus → intacte
        {},  # vide → intacte
        # payload métier légitime contenant une clé "args" → NE PAS déplier
        {"result": "ok", "args": [{"brief": "b"}]},
    ],
)
def test_valid_shapes_pass_through_untouched(args: dict) -> None:
    assert unwrap_return_envelope(args) is args or args == {
        "result": {"brief": "b", "shots": []}
    }


def test_install_patches_strategy_and_unwraps_end_to_end() -> None:
    """Bout-en-bout via le vrai handler NOOA : l'enveloppe fautive devient
    une instance validée au lieu d'un GenerationError après 3 essais."""
    install()
    from nooa.strategies.codeact import CodeActStrategy

    strategy = CodeActStrategy()
    runtime = MagicMock()
    runtime.get_generation_id.return_value = "gen-1"
    session = MagicMock()
    session.session_locals = {}
    call = MagicMock()
    call.method_name = "plan_scene"

    envelope = {
        "args": [{"brief": "Cyberpunk alley", "shots": ["shot-1"]}],
        "function_name": "TinySpec",
    }
    validated, error_msg = strategy._handle_return_result(
        runtime=runtime,
        tool_call=None,
        args=envelope,
        return_type=TinySpec,
        session=session,
        call=call,
    )
    assert error_msg is None
    assert isinstance(validated, TinySpec)
    assert validated.brief == "Cyberpunk alley"
    assert validated.shots == ["shot-1"]


def test_install_is_idempotent() -> None:
    from nooa.strategies.codeact import CodeActStrategy

    install()
    first = CodeActStrategy._handle_return_result
    install()
    assert CodeActStrategy._handle_return_result is first


def _call_real_handler(
    args: dict, return_type: Any = StorySpec
) -> tuple[Any, str | None]:
    install()
    from nooa.strategies.codeact import CodeActStrategy

    strategy = CodeActStrategy()
    runtime = MagicMock()
    runtime.get_generation_id.return_value = "gen-1"
    session = MagicMock()
    session.session_locals = {}
    call = MagicMock()
    call.method_name = "plan_story"
    return strategy._handle_return_result(
        runtime=runtime,
        tool_call=None,
        args=args,
        return_type=return_type,
        session=session,
        call=call,
    )


def test_empty_logline_repaired_from_synopsis_end_to_end() -> None:
    """Régression du log 19:47 : logline vide → invariant → run tué.
    Désormais la première phrase du synopsis devient logline AVANT validation."""
    envelope = {
        "args": [{
            "logline": "",
            "synopsis": "Une hackeuse découvre que ses souvenirs ont été vendus. "
            "Elle remonte la piste jusqu'à son propre frère.",
            "genre": "thriller",
            "tone": "sombre",
        }],
        "function_name": "StorySpec",
    }
    validated, error_msg = _call_real_handler(envelope)
    assert error_msg is None
    assert isinstance(validated, StorySpec)
    assert validated.logline == "Une hackeuse découvre que ses souvenirs ont été vendus."


def test_empty_logline_fallback_when_nothing_derivable() -> None:
    """Aucun champ dérivable : logline de repli, le run survit quand même."""
    validated, error_msg = _call_real_handler({"args": [{}], "function_name": "StorySpec"})
    assert error_msg is None
    assert isinstance(validated, StorySpec)
    assert validated.logline.strip()


def test_result_key_payload_logline_also_repaired() -> None:
    """Forme canonique return_result(result={...}) : même réparation."""
    validated, error_msg = _call_real_handler(
        {"result": {"logline": "", "synopsis": "Deux amis. Un secret."}}
    )
    assert error_msg is None
    assert isinstance(validated, StorySpec)
    assert "Deux amis" in validated.logline


def test_filled_logline_left_untouched() -> None:
    validated, error_msg = _call_real_handler(
        {"args": [{"logline": "Ma logline", "synopsis": "Autre chose."}],
         "function_name": "StorySpec"}
    )
    assert error_msg is None
    assert validated.logline == "Ma logline"


def test_structural_invariants_still_strict() -> None:
    """La réparation ne doit PAS affaiblir les invariants structurels :
    SceneSpec sans shots reste rejeté, StorySpec vide reste attrapé par
    la postcondition si elle est enregistrée (filet de sécurité)."""
    import pytest as _pytest

    from deepblender.agents.base import scene_spec_postcondition, story_spec_postcondition
    from deepblender.domain.scene import SceneSpec
    from nooa.strategy_validation import InvariantError

    with _pytest.raises(InvariantError):
        scene_spec_postcondition(None, SceneSpec(brief="x"), None)
    with _pytest.raises(InvariantError):
        story_spec_postcondition(None, StorySpec(logline=""), None)


def test_storyboard_shots_as_raw_dicts_coerced_end_to_end() -> None:
    """Régression du log 21:19 : NOOA valide StoryboardSpec sans conversion
    récursive → shots restent des dicts → to_mapping plante sur s.index.
    Le shim doit livrer de vraies StoryboardShot."""
    install()
    from nooa.strategies.codeact import CodeActStrategy

    strategy = CodeActStrategy()
    runtime = MagicMock()
    runtime.get_generation_id.return_value = "gen-2"
    session = MagicMock()
    session.session_locals = {}
    call = MagicMock()
    call.method_name = "plan_storyboard"

    # Scénario du log 21:19 : le CODE du modèle a construit l'instance
    # directement avec des dicts dedans ; le chemin « result=instance »
    # court-circuite la validation stricte des champs de NOOA.
    dirty = StoryboardSpec()
    dirty.total_duration = 12.0
    dirty.shots = [
        {"description": "plan large du laboratoire",
         "camera_angle": "wide", "camera_movement": "dolly"},
        {"description": "gros plan sur l'écran"},
    ]
    validated, error_msg = strategy._handle_return_result(
        runtime=runtime, tool_call=None, args={"result": dirty},
        return_type=StoryboardSpec, session=session, call=call,
    )
    assert error_msg is None
    assert isinstance(validated, StoryboardSpec)
    assert all(isinstance(s, StoryboardShot) for s in validated.shots)
    assert validated.shots[0].index == 0 and validated.shots[1].index == 1
    assert validated.shots[1].camera_movement == "static"  # défauts appliqués
    assert abs(validated.total_duration - 12.0) < 1e-9
    assert validated.id == dirty.id  # identité préservée
    # La sérialisation qui tuait le run fonctionne désormais :
    mapping = validated.to_mapping()
    assert mapping["shots"][0]["description"] == "plan large du laboratoire"


def test_story_spec_with_dict_acts_and_dialogues_coerced() -> None:
    validated, error_msg = _call_real_handler({
        "result": {
            "logline": "Une nuit décisive.",
            "acts": [{"name": "I", "order": 0,
                      "beats": [{"description": "ouverture"}]}],
            "dialogues": [{"character": "Awa", "text": "On y va ?"}],
        }
    })
    assert error_msg is None
    assert isinstance(validated, StorySpec)
    from deepblender.domain.narrative import Act, DialogueLine

    assert isinstance(validated.acts[0], Act)
    assert isinstance(validated.acts[0].beats[0], object)  # StoryBeat
    assert isinstance(validated.dialogues[0], DialogueLine)


def test_domain_serializers_tolerate_raw_dicts_belt() -> None:
    """Ceinture de sécurité : même SANS coercition amont, to_mapping ne
    doit plus planter sur des dicts bruts (log 21:19)."""
    raw_storyboard = StoryboardSpec(shots=[
        {"index": 0, "description": "brut", "duration": 4.0},
    ])
    mapping = raw_storyboard.to_mapping()
    assert mapping["shots"][0]["index"] == 0

    raw_story = StorySpec(acts=[{"name": "I", "beats": []}],
                          dialogues=[{"character": "A", "text": "b"}])
    smapping = raw_story.to_mapping()
    assert smapping["acts"][0]["name"] == "I"
    assert smapping["dialogues"][0]["text"] == "b"


def test_stringified_tool_call_result_parsed_end_to_end() -> None:
    """Régression du log 21:34 : le modèle passe à return_result une CHAÎNE
    JSON contenant l'appel d'outil entier sérialisé. Le payload interne est
    valide — il doit être extrait, coercé et validé au lieu de tuer le run."""
    import json as _json

    stringified = _json.dumps({
        "type": "function",
        "name": "StoryboardSpec",
        "parameters": {
            "shots": [{
                "camera_angle": "wide", "camera_movement": "static",
                "description": "Plan large du laboratoire",
                "duration": 3.5, "index": 0,
            }],
            "total_duration": 10.0,
            "id": "1a3990a1",
            "schema_version": 1,
        },
    })
    install()
    from nooa.strategies.codeact import CodeActStrategy

    strategy = CodeActStrategy()
    runtime = MagicMock()
    runtime.get_generation_id.return_value = "gen-3"
    session = MagicMock()
    session.session_locals = {}
    call = MagicMock()
    call.method_name = "plan_storyboard"

    validated, error_msg = strategy._handle_return_result(
        runtime=runtime, tool_call=None,
        args={"result": stringified},
        return_type=StoryboardSpec, session=session, call=call,
    )
    assert error_msg is None
    assert isinstance(validated, StoryboardSpec)
    assert isinstance(validated.shots[0], StoryboardShot)
    assert validated.shots[0].description == "Plan large du laboratoire"
    assert abs(validated.total_duration - 10.0) < 1e-9


def test_parse_json_string_result_edge_cases() -> None:
    """Chaîne non JSON / non objet / sans rapport → intouchées."""
    untouched = [
        {"result": "bonjour"},                      # texte libre
        {"result": "[1, 2]"},                       # tableau, pas un objet
        {"result": "{pas du json}"},                # JSON invalide
        {"brief": "x"},                             # pas de clé result
    ]
    for args in untouched:
        assert parse_json_string_result(args) is args or parse_json_string_result(args) == args

    # Payload nu (sans enveloppe tool-call) dans la chaîne :
    bare = parse_json_string_result({"result": '{"logline": "L.", "synopsis": "S."}'})
    assert bare["result"] == {"logline": "L.", "synopsis": "S."}

    # Enveloppe arguments/name :
    wrapped = parse_json_string_result(
        {"result": '{"arguments": {"total_duration": 5.0}, "name": "StoryboardSpec"}'}
    )
    assert wrapped["result"] == {"total_duration": 5.0}

    # Clés d'enveloppe seules SANS payload exploitable → intouché :
    orphan = {"result": '{"type": "function", "name": "X"}'}
    assert parse_json_string_result(orphan) == orphan


def test_pretty_printed_stringified_tool_call_parsed() -> None:
    """Régression du log 22:49 : la chaîne JSON est pretty-printée avec de
    VRAIS sauts de ligne DANS les valeurs → json.loads strict échoue.
    strict=False doit restaurer le payload."""
    raw = (
        '{\n  "type": "function",\n  "name": "build_script",\n'
        '  "parameters": {"logline": "L.", "synopsis": "S1.\nS2."}\n}'
    )
    parsed = parse_json_string_result({"result": raw})
    assert parsed["result"] == {"logline": "L.", "synopsis": "S1.\nS2."}


def test_markdown_fenced_json_parsed() -> None:
    raw = '```json\n{"logline": "L.", "synopsis": "S."}\n```'
    parsed = parse_json_string_result({"result": raw})
    assert parsed["result"] == {"logline": "L.", "synopsis": "S."}


def test_typed_wrapper_and_single_key_unwrapped_end_to_end() -> None:
    """Forme exacte du log 22:49 (contenu salvable) :
    result={"spec": {"type": T, "value": {...payload...}}} → payload validé."""
    args = {
        "result": {
            "spec": {
                "type": "StorySpec",
                "value": {"logline": "Une nuit décisive.", "synopsis": "S."},
            }
        }
    }
    validated, error_msg = _call_real_handler(args)
    assert error_msg is None
    assert isinstance(validated, StorySpec)
    assert validated.logline == "Une nuit décisive."


def test_call_envelope_dict_unwrapped_end_to_end() -> None:
    """Enveloppe tool-call passée en DICT (pas en chaîne) → payload extrait."""
    args = {
        "result": {
            "type": "function",
            "name": "build_script",
            "parameters": {"code": "import bpy\n", "scene_name": "scene_x"},
        }
    }
    validated, error_msg = _call_real_handler(args, return_type=BlenderScript)
    assert error_msg is None
    assert isinstance(validated, BlenderScript)
    assert validated.scene_name == "scene_x"


def test_blender_script_direct_typed_wrapper() -> None:
    """Wrapper typé direct sans clé englobante : {"type": T, "value": {...}}."""
    args = {
        "result": {
            "type": "BlenderScript",
            "value": {"code": "import bpy\n", "scene_name": "scene_y"},
        }
    }
    validated, error_msg = _call_real_handler(args, return_type=BlenderScript)
    assert error_msg is None
    assert isinstance(validated, BlenderScript)


def test_unwrap_typed_wrappers_non_interference() -> None:
    """Payloads légitimes intouchés."""
    untouched = [
        {"result": {"shots": [{"description": "a"}]}},   # liste → pas de descente
        {"result": {"value": 3}},                        # valeur non-dict
        {"result": {"type": "x"}},                       # pas de paire type/value
        {"result": {"logline": "L", "synopsis": "S"}},   # payload multi-champs
        {"brief": "x"},                                  # pas de clé result
    ]
    for args in untouched:
        assert unwrap_typed_wrappers(args) is args


def test_positional_args_envelope_mapped_end_to_end() -> None:
    """Régression du log 23:21 : le modèle passe les valeurs POSITIONNELLES
    (ordre de déclaration des champs) au lieu d'un dict par champs."""
    args = {"args": [True, 0.85, [], []], "function_name": "QAReport"}
    validated, error_msg = _call_real_handler(args, return_type=QAReport)
    assert error_msg is None
    assert isinstance(validated, QAReport)
    assert validated.passed is True
    assert validated.score == 0.85


def test_positional_args_prefix_mapped() -> None:
    """Préfixe seulement ([passed, score]) : les champs à défaut complètent."""
    args = {"args": [False, 0.4], "function_name": "QAReport"}
    validated, error_msg = _call_real_handler(args, return_type=QAReport)
    assert error_msg is None
    assert isinstance(validated, QAReport)
    assert validated.issues == []
    assert validated.recommendations == []


def test_positional_args_with_excess_truncated() -> None:
    """Régression du log 23:52 : 5ᵉ argument excédentaire ('PASS', propriété
    calculée recopiée) → tronqué aux champs déclarés, pas d'enveloppe rejetée."""
    args = {"args": [True, 0.85, [], [], "PASS"], "function_name": "QAReport"}
    validated, error_msg = _call_real_handler(args, return_type=QAReport)
    assert error_msg is None
    assert isinstance(validated, QAReport)
    assert validated.passed is True
    assert validated.score == 0.85


def test_positional_args_guards() -> None:
    from deepblender.nooa_compat import map_positional_args

    # Type sans champs connus → intouché :
    unknown = {"args": [1, 2], "function_name": "X"}
    assert map_positional_args(unknown, int) is unknown
    # Clés hors enveloppe → intouché :
    other = {"args": [True], "weird": 1}
    assert map_positional_args(other, QAReport) is other
