"""Découplage NOOA (palier 3 de la CI).

Deux propriétés structurelles :
1. Les agents DeepBlender sont des sous-classes directes de `nooa.Agent`
   (aucun runtime agentique propriétaire).
2. Le domaine métier, le codegen, les artifacts, la production, le bridge
   Blender et l'API n'importent PAS nooa : NOOA est encapsulé derrière les
   agents et le mécanisme de skills uniquement.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from nooa import Agent
from nooa.unifiedllm import FakeLLMClient

from deepblender.agents import (
    AudioAgent,
    BlenderAgent,
    CompositingAgent,
    DirectorAgent,
    LocalizationAgent,
    QAAgent,
)
from deepblender.domain.qa import IssueKind

PACKAGE = Path(__file__).resolve().parent.parent / "deepblender"

# Modules qui DOIVENT rester indépendants de nooa.
NOOA_FREE_DIRS = ("domain", "codegen", "artifacts", "production", "bridge", "blender", "api", "plugins")

# Modules qui UTILISENT nooa de façon intentionnelle.
NOOA_ALLOWED_FILES = (
    "agents/audio.py",
    "agents/blender.py",
    "agents/compositing.py",
    "agents/director.py",
    "agents/localization.py",
    "agents/qa.py",
    "skills/registry.py",
)


def _file_imports_nooa(module_file: Path) -> bool:
    tree = ast.parse(module_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name == "nooa" or alias.name.startswith("nooa.") for alias in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("nooa"):
            return True
    return False


def _package_py_files() -> list[Path]:
    return [p for p in PACKAGE.rglob("*.py") if p.name != "__init__.py"]


def test_domain_layers_never_import_nooa() -> None:
    offenders: list[str] = []
    for module_file in _package_py_files():
        relative = module_file.relative_to(PACKAGE).as_posix()
        top_dir = relative.split("/", maxsplit=1)[0]
        if top_dir in NOOA_FREE_DIRS and _file_imports_nooa(module_file):
            offenders.append(relative)
    assert offenders == [], f"modules du domaine importent nooa : {offenders}"


def test_agents_and_skill_mechanism_may_use_nooa() -> None:
    for relative in NOOA_ALLOWED_FILES:
        assert (PACKAGE / relative).is_file(), f"module attendu absent : {relative}"


@pytest.mark.parametrize(
    "agent_cls",
    [AudioAgent, BlenderAgent, CompositingAgent, DirectorAgent, LocalizationAgent, QAAgent],
)
def test_agents_are_nooa_agents(agent_cls: type[Agent]) -> None:
    assert issubclass(agent_cls, Agent)


@pytest.mark.parametrize(
    "method",
    [
        DirectorAgent.plan_scene,
        BlenderAgent.build_script,
        QAAgent.assess,
        AudioAgent.plan_audio,
        CompositingAgent.plan_compositing,
        LocalizationAgent.plan_localization,
    ],
)
def test_agentic_methods_are_coroutines(method: object) -> None:
    assert inspect.iscoroutinefunction(method)


def test_deterministic_bodies_are_pure_python() -> None:
    llm = FakeLLMClient()
    director = DirectorAgent(llm=llm)
    assert director.default_shot_duration() == 5.0

    blender = BlenderAgent(llm=llm)
    assert blender.frame_count(5.0, 24) == 120

    qa = QAAgent(llm=llm)
    issues = qa.technical_check("")
    assert issues and issues[0].kind is IssueKind.TECHNICAL

    audio = AudioAgent(llm=llm)
    assert audio.default_music_volume() == 0.4

    compositing = CompositingAgent(llm=llm)
    assert compositing.default_output_format() == "exr"

    localization = LocalizationAgent(llm=llm)
    assert localization.default_language() == "fr"
    assert localization.default_languages() == ["fr"]


def test_agents_apply_truncation_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPBLENDER_AGENT_TRUNCATION", "1")
    monkeypatch.setenv("LLM_CONTEXT_TOKENS", "32000")

    director = DirectorAgent(llm=FakeLLMClient())

    assert director._truncation is not None
    assert director._truncation.max_context_tokens == 32000
    assert director._truncation.min_preserved_events == 8
    assert director._truncation.response_reserve_tokens == 2048


def test_agents_use_sqlite_storage_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "agent.db"
    monkeypatch.setenv("DEEPBLENDER_AGENT_STORAGE", str(db))

    director = DirectorAgent(llm=FakeLLMClient())

    assert director._storage is not None
    assert db.exists()


def test_scene_spec_postcondition_rejects_empty_shots() -> None:
    from nooa.strategy_validation import InvariantError

    from deepblender.agents.base import scene_spec_postcondition
    from deepblender.domain.scene import SceneSpec

    with pytest.raises(InvariantError):
        scene_spec_postcondition(None, SceneSpec(brief="x"), None)


def test_scene_spec_postcondition_accepts_spec_with_shots() -> None:
    from deepblender.agents.base import scene_spec_postcondition
    from deepblender.domain.scene import SceneSpec, ShotSpec

    spec = SceneSpec(brief="x", shots=[ShotSpec()])
    # Aucune levée = pas d'InvariantError
    scene_spec_postcondition(None, spec, None)


def test_blender_script_postcondition_rejects_empty_code() -> None:
    from nooa.strategy_validation import InvariantError

    from deepblender.agents.base import blender_script_postcondition
    from deepblender.domain.scene import BlenderScript

    with pytest.raises(InvariantError):
        blender_script_postcondition(None, BlenderScript(code="", scene_name="s"), None)


def test_blender_script_postcondition_accepts_valid_code() -> None:
    from deepblender.agents.base import blender_script_postcondition
    from deepblender.domain.scene import BlenderScript

    blender_script_postcondition(
        None, BlenderScript(code="import bpy\nscene = bpy.context.scene", scene_name="s"), None
    )


def test_no_generic_runtime_reimplementation() -> None:
    """Aucun des concepts interdits (Roadmap C §40) ne doit exister."""
    forbidden = (
        "GenericAgentRuntime",
        "GenericAgentLoop",
        "GenericContextManager",
        "GenericMemoryManager",
        "GenericEventBus",
        "GenericStateManager",
        "GenericLLMOrchestrator",
        "GenericWorkflowEngine",
        "GenericHandoffEngine",
        "GenericTracingSystem",
    )
    for module_file in _package_py_files():
        source = module_file.read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in source, f"{module_file.relative_to(PACKAGE)} contient {name}"
