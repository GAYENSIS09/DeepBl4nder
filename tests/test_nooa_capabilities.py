"""Couverture des capacités NOOA 0.0.8 exploitées par les agents DeepBl4nder.

Vérifie sans réseau (FakeLLMClient) :
- TemplateStrategy  : ``build_probe_script`` déterministe, zéro appel LLM
- ReflexionStrategy : ``refine_script`` (boucle génération + évaluation)
- PredictStrategy   : ``quick_scan`` (tour unique, sortie typée QAReport)
- CodeActLiteStrategy : ``plan_compositing``
- Contexte dynamique + ``agentdoc.pformat`` (résumé de spec réévalué)
- Événements NOOA (``self.events.query``) via ``recent_run_history``
- EventQuery configuré par environnement (filtre des événements injectés)
- Mémoire long terme (nooa-memory) : remember / recall
- MCP : découverte des serveurs sans connexion
"""

from __future__ import annotations

import json

import pytest
from nooa.strategies.codeact_lite import CodeActLiteStrategy
from nooa.strategies.predict import PredictStrategy
from nooa.strategies.reflexion import ReflexionStrategy

from DeepBl4nder.agents import BlenderAgent, CompositingAgent, QAAgent
from DeepBl4nder.agents.base import BaseAgent
from DeepBl4nder.domain.qa import QAReport
from DeepBl4nder.domain.scene import (
    BlenderScript,
    CharacterSpec,
    SceneSpec,
    ShotSpec,
)


def _spec() -> SceneSpec:
    return SceneSpec(
        brief="Une ruelle sombre sous la pluie.",
        characters=[CharacterSpec(name="Nina", main_language="fr")],
        shots=[ShotSpec(duration=5.0, fps=24)],
    )


def _response(content: str):
    from nooa.unifiedllm import LLMResponse

    return LLMResponse(
        raw_response={"choices": [{"message": {"content": content}}]},
        content=content,
        tool_calls=[],
        finish_reason="stop",
        assistant_message={"role": "assistant", "content": content},
        reasoning=None,
        usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    )


# ------------------------------------------------------- TemplateStrategy


def test_build_probe_script_is_deterministic_without_llm() -> None:
    import asyncio

    from nooa.unifiedllm import FakeLLMClient

    llm = FakeLLMClient()
    agent = BlenderAgent(llm=llm)

    script = asyncio.run(agent.build_probe_script("ruelle_sombre"))
    assert isinstance(script, BlenderScript)
    assert script.scene_name == "ruelle_sombre"
    assert "ruelle_sombre" in script.code
    assert "bpy" in script.code

    again = asyncio.run(agent.build_probe_script("ruelle_sombre"))
    assert again.code == script.code
    # TemplateStrategy : aucune génération LLM n'est consommée
    assert llm.call_count == 0


# ------------------------------------------------------- ReflexionStrategy


def test_refine_script_runs_reflexion_loop() -> None:
    import asyncio

    from nooa.unifiedllm import FakeLLMClient

    llm = FakeLLMClient(
        scripted_responses=[
            _response(
                json.dumps(
                    {
                        "code": "import bpy\n# revised\n",
                        "scene_name": "ruelle",
                        "version": 3,
                    }
                )
            ),
            _response(
                json.dumps(
                    {
                        "is_satisfactory": True,
                        "issues": [],
                        "suggestions": [],
                        "reasoning": "ok",
                    }
                )
            ),
        ]
    )
    agent = BlenderAgent(llm=llm)

    revised = asyncio.run(agent.refine_script(_spec(), revision_feedback="Trop sombre", version=3))
    assert isinstance(revised, BlenderScript)
    assert revised.version == 3
    assert revised.code.strip()
    assert llm.call_count >= 2  # génération + évaluation de la réflexion


def test_refine_script_strategy_is_reflexion() -> None:
    strategy = BlenderAgent.__dict__["refine_script"]._plan_strategy
    assert isinstance(strategy, ReflexionStrategy)


# ------------------------------------------------------- PredictStrategy


def test_quick_scan_returns_typed_qa_report() -> None:
    import asyncio

    from nooa.unifiedllm import FakeLLMClient

    llm = FakeLLMClient(
        scripted_responses=[
            _response(
                json.dumps(
                    {
                        "value": {
                            "passed": True,
                            "score": 0.8,
                            "issues": [],
                            "recommendations": ["Ajouter de la brume"],
                        }
                    }
                )
            )
        ]
    )
    agent = QAAgent(llm=llm)

    report = asyncio.run(agent.quick_scan("import bpy\n", _spec()))
    assert isinstance(report, QAReport)
    assert report.passed is True
    assert report.score == 0.8
    assert llm.call_count == 1  # PredictStrategy : un seul tour


def test_quick_scan_strategy_is_predict() -> None:
    strategy = QAAgent.__dict__["quick_scan"]._plan_strategy
    assert isinstance(strategy, PredictStrategy)


# ------------------------------------------------------- CodeActLiteStrategy


def test_plan_compositing_strategy_is_code_act_lite() -> None:
    strategy = CompositingAgent.__dict__["plan_compositing"]._plan_strategy
    assert isinstance(strategy, CodeActLiteStrategy)

# -------------------------------------------------- contexte dynamique


def test_dynamic_context_uses_agentdoc_pformat() -> None:
    from nooa.unifiedllm import FakeLLMClient

    agent = BlenderAgent(llm=FakeLLMClient())
    summary = agent._current_scene_summary(_spec())
    assert "ruelle sombre" in summary
    assert "Nina" in summary
    assert "shots" in summary

    agent._set_dynamic("scene_summary", "self._current_scene_summary(self._last_spec)")
    assert "scene_summary" in agent.context.keys()
    # Valeur résolue au tour suivant (DynamicNotResolvedError avant le premier tour)
    with pytest.raises(Exception):
        agent.context["scene_summary"]


# ------------------------------------------------------- événements NOOA


def test_recent_run_history_reads_agent_events() -> None:
    import asyncio

    from nooa.unifiedllm import FakeLLMClient

    agent = BlenderAgent(llm=FakeLLMClient())
    assert agent.recent_run_history() == []

    agent = BlenderAgent(
        llm=FakeLLMClient(
            scripted_responses=[
                _response(
                    json.dumps(
                        {
                            "code": "import bpy\n",
                            "scene_name": "ruelle",
                            "version": 2,
                        }
                    )
                ),
                _response(
                    json.dumps(
                        {
                            "is_satisfactory": True,
                            "issues": [],
                            "suggestions": [],
                            "reasoning": "ok",
                        }
                    )
                ),
            ]
        )
    )
    asyncio.run(agent.refine_script(_spec(), revision_feedback="brighten"))
    history = agent.recent_run_history(limit=20)
    assert history, "des événements NOOA doivent exister après un run agentique"
    assert any("[" in row and "]" in row for row in history)


def test_event_query_wired_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DeepBl4nder_EVENT_QUERY", "Task")
    from nooa.unifiedllm import FakeLLMClient

    agent = BaseAgent(llm=FakeLLMClient())
    query = agent.event_query
    assert query is not None
    assert query.type == "Task"


def test_get_model_id_prefers_real_router_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_get_model_id`` affiche le vainqueur réel du routeur (rotation),
    pas le modèle statique du premier fournisseur du pool."""
    from DeepBl4nder import llm
    from nooa.unifiedllm import FakeLLMClient

    class _FakeRouter(FakeLLMClient):
        def __init__(self, last_provider: str, last_model: str, static_model: str) -> None:
            super().__init__(scripted_responses=["ok"])
            self._last_provider_id = last_provider
            self._last_model = last_model
            self.model = static_model

        @property
        def last_provider_id(self) -> str | None:
            return self._last_provider_id

        @property
        def last_model(self) -> str | None:
            return self._last_model

    router = _FakeRouter("groq", "groq/openai/gpt-oss-120b", "gemini/gemini-3.7-flash")
    agent = BaseAgent(llm=router)
    assert agent._get_model_id() == "groq/openai/gpt-oss-120b"
    assert agent._get_last_call_info() == {
        "provider": "groq",
        "model": "groq/openai/gpt-oss-120b",
    }

    # Jamais de décision réelle → un routeur ne prétend pas utiliser la
    # config statique : modèle vide (l'UI affiche "(no reply yet)").
    agent2 = BaseAgent(llm=_FakeRouter(None, None, "gemini/gemini-3.7-flash"))
    assert agent2._get_model_id() == ""
    assert agent2._get_last_call_info() == {}

    # Client non-routeur (pas de ``last_provider_id``) : la config exposée
    # EST le modèle réel.
    agent3 = BaseAgent(llm=FakeLLMClient(scripted_responses=["ok"]))
    assert agent3._get_model_id() == agent3._llm.model


# ------------------------------------------------------- mémoire long terme


@pytest.mark.skipif(
    not __import__("importlib.util").util.find_spec("nooa_memory"),
    reason="extra nooa[memory] requis",
)
def test_memory_remember_and_recall(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from nooa.unifiedllm import FakeLLMClient
    from nooa_memory.manager import MemoryType  # type: ignore[import-untyped]

    monkeypatch.setenv("MEMORY_STORAGE_PATH", str(tmp_path))
    agent = BaseAgent(llm=FakeLLMClient(), memory=True)
    assert agent.memory is not None
    assert agent.memory_skill() is not None

    agent.memory.remember(
        "scene ruelle sombre sous la pluie",
        type=MemoryType.INFO,
        tags=["scene", "ruelle"],
    )
    found = agent.memory.recall("ruelle pluie")
    assert any("ruelle" in m.content for m in found)


# ------------------------------------------------------- validate helpers


def test_validate_script_detects_empty_code() -> None:
    from nooa.unifiedllm import FakeLLMClient

    agent = BlenderAgent(llm=FakeLLMClient())
    bad = BlenderScript(code="", scene_name="x")
    assert agent.validate_script(bad) == ["code vide"]

    good = BlenderScript(code="import bpy\n", scene_name="x")
    assert agent.validate_script(good) == []


def test_validate_spec_detects_no_shots() -> None:
    from nooa.unifiedllm import FakeLLMClient

    from DeepBl4nder.agents.director import DirectorAgent

    d = DirectorAgent(llm=FakeLLMClient())
    empty = SceneSpec(brief="vide")
    assert d.validate_spec(empty) == ["aucun plan"]

    with_shots = SceneSpec(brief="ok", shots=[ShotSpec()])
    assert d.validate_spec(with_shots) == []
