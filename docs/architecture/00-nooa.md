# 00 — NOOA : matrice de capacités réelles (0.0.8)

> **Objet :** savoir exactement ce que NOOA 0.0.8 fournit pour ne RIEN réimplémenter.
> **Source :** audit direct du paquet installé (`nooa==0.0.8`, Apache-2.0) + arXiv:2607.20709.
> Cet audit répond à la Phase 0 de la roadmap originale (« NOOA audit »).

## Le paradigme

> **Un agent est un objet Python.** Ses méthodes sont les actions que le modèle peut prendre,
> ses champs sont son état, ses docstrings sont ses prompts, ses annotations de type sont ses
> contrats. Une méthode dont le corps est `...` est complétée à l'exécution par une boucle
> agentique pilotée par LLM ; une méthode au corps Python normal reste du code déterministe.

C'est le cœur de NOOA : la métaclasse `AgentMeta` détecte les corps `...` au chargement de la
classe (`nooa/metaclass.py`) et génère le code d'exécution correspondant.

## Matrice de capacités

| Capacité | Symbole réel | Signature (résumé) | Notes |
|---|---|---|---|
| Agent (classe de base) | `nooa.Agent` | `class Agent(metaclass=AgentMeta)` | `nooa/agent.py:74` |
| Config classe agent | `Agent.__init_subclass__` | `(llm=INHERIT, truncation=None, execution=None, context=None, event_query=None)` | `nooa/agent.py:128` ; `context` = `dict[str, str \| DynamicContext \| None]` |
| Config instance agent | `Agent.__init__` | `(llm=INHERIT, *, truncation, render_config, context, event_query, storage)` | `nooa/agent.py:167` |
| Résolution LLM en cascade | `Agent._resolve_llm` | instance → classe → parent runtime | `nooa/agent.py:289` |
| Contexte (API modèle) | `self.context` (`ContextApi`) | `set`, `set_dynamic`, `set_static`, `get`, `pop`, `keys`, `attach`/`detach` | `nooa/runtime/context.py` |
| Contexte dynamique | `nooa.DynamicContext` | `DynamicContext("expr")` réévalué chaque tour | `nooa/context_blocks/` |
| Événements (API modèle) | `self.events` (`EventsApi`) | `query`, `get`, `keys`, `collapse`, `attach` | `nooa/runtime/events.py` |
| Events / EventQuery | `nooa.EventQuery` | filtrage des événements injectés dans le contexte | `nooa/runtime/event_query.py` |
| Génération | `self.runtime.generate` | `(*, tools=None, output_model=None, **kw) -> (LLMResponse, event_id)` | `nooa/runtime/actor.py:858` |
| Référence d'appel courant | `self.runtime.current_call` | `CurrentCall(id, args, kwargs)` | utilisable dans une expression DynamicContext |
| Exécution de code | `self.runtime` | exécution sérialisée + capture stdout/stderr | `nooa/runtime/actor.py` |
| Stratégies | `nooa.PredictStrategy`, `nooa.CodeActStrategy`, `nooa.CodeActLiteStrategy`, `ReflexionStrategy`, `TemplateStrategy` | configurables par classe/méthode via `@strategy` | `nooa/strategies/` |
| Stratégie par défaut | `nooa.set_default_strategy`, `nooa.get_default_strategy` | `nooa/strategies/__init__.py` | |
| Contrats entrée/sortie | annotations de type + `output_model` | validation de sortie et retry de validation | `nooa/strategy_validation.py` |
| Pré/postconditions | `MethodPrecondition`, `MethodPostcondition`, `InvariantError` | pré → fail fast ; post → retry validation | `nooa/strategy_validation.py` |
| Code-as-Action | `CodeActStrategy` | bloc `execution_context`, prefill `InspectInputsPrefill` | `nooa/strategies/codeact.py:287` |
| Skills | `nooa.Skill`, `nooa.TextSkill` | `TextSkill(path=..., id=...)` lit `SKILL.md` (frontmatter) ; `run_script`, `read_file` ; `@slash_command` | `nooa/skill.py:290,353` |
| Registry de skills | `nooa.skill_registry`, `nooa.skill_from_module` | entry-points `[nooa.skills]` (`nemo.context`, `nemo.events`, `nemo.libwriting`, …) | `nooa/__init__.py` |
| Mémoire long terme | `nooa-memory` (extra `nooa[memory]`) | extension séparée | extra optionnel |
| Persistance / stockage | `nooa.storage.StorageManager`, `SQLiteStorageManager` | `Agent(storage=...)` | `nooa/storage/sqlite.py` |
| Tracing | `nooa.enable_tracing`, viewer `trace-explorer`, `python -m nooa.viewer` | OTLP, port viewer 5001 | `nooa/tracing/`, `nooa/viewer/` |
| MCP | `nooa.mcp` (`MCPTool`, `MCPManager`) | extra `nooa[mcp]` | `nooa/mcp/tool.py:596,713` |
| Sandbox | `execution_backend="sandbox"` dans `CodeActConfig` | frontière de confinement à combiner avec un vrai sandbox OS | `nooa/strategies/codeact.py` |
| Agentdoc | `nooa.agentdoc` (`spec`, `hidden`, `doc`, `pformat`, `pprint`) | rendu d'objets pour le modèle | `nooa/agentdoc/__init__.py` |
| Config de modèle | `nooa.unifiedllm.get_llm_client`, registre `MODELS` | `LLM_BASE_URL` / `LLM_API_KEY` compatibles litellm | `nooa/unifiedllm/registry.py` |
| LLM de test | `nooa.unifiedllm.fake.FakeLLMClient` | `FakeLLMClient(scripted_responses=...)`, `with_code_responses`, `simple_message` | sous-classe de `UnifiedLLM` |
| Truncation | `nooa.config.TruncationConfig` | `max_context_tokens`, `max_event_tokens`, `min_preserved_events`, `response_reserve_tokens` | `nooa/config/truncation_config.py:170` |

## Variables d'environnement reconnues par NOOA

- **Config** : `NEMO_OO_SECRETS`, `NEMO_OO_LLM_CONFIG`, `NEMO_OO_SETTINGS`, `NEMO_OO_USER_DIR`, `NEMO_OO_PROJECT_DIR`, `XDG_CONFIG_HOME`, `NEMO_OO_MODELS_CONFIG`.
- **Viewer / tracing** : `NOOA_VIEWER_AUTH_TOKEN`, `NOOA_TRACE_VIEWER_PORT`/`NEMO_OO_TRACE_VIEWER_PORT`, `NOOA_TRACE_DB`/`NEMO_OO_TRACE_DB`, `OTLP_ENDPOINT`, `OTLP_PROBE_TIMEOUT`, `TRACE_DIR`, `TRACE_EXPERIMENT`, `LANGFUSE_*`, `NEMO_TRACE_KEEP_LLM_VALUES`.
- **Clés LLM** : `NVIDIA_INFERENCE_API_KEY`, `NVIDIA_INTERNAL_API_KEY`, `NVIDIA_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
- **Divers** : `SSL_CERTIFICATE`, `DISABLE_AIOHTTP_TRANSPORT`, `ATIF_OUTPUT_DIR`.

## Exemple minimal d'agent NOOA hérité (compilable)

```python
from nooa import Agent, CodeActStrategy, strategy

class DirectorAgent(Agent):
    """You are a film director who turns a brief into a typed SceneSpec.

    <state>renders your current fields each turn</state>
    """

    def deterministic_helpers(self) -> int:  # corps Python = déterministe
        return 42

    @strategy(CodeActStrategy())
    async def plan_scene(self, brief: str) -> "SceneSpec":
        """Turn the creative brief into a structured scene specification."""
        ...  # corps = agentique

director = DirectorAgent(llm=FakeLLMClient())  # ou client réel
```

Points clés :
- Omit `llm` pour activer la résolution en cascade (classe → parent).
- `context`/`events` sur l'instance (`self.context.set(...)`, `self.events.query(...)`) sont les
  API modèle ; `context_manager`/`event_manager` sont les API de framework.
- `self.runtime.generate(output_model=...)` permet un contrôle plus fin dans les méthodes déterministes.

## Limites / points bloquants relevés

1. **LLM requis à l'instanciation** : `Agent(...)` sans LLM résolu lève `ValueError` (`nooa/agent.py:322`).
2. **`visible` est un no-op** : tout est visible par défaut ; `@hidden` (agentdoc) reste l'outil de masquage.
3. **Sandbox** : NOOA dispose d'un `execution_backend="sandbox"` mais sa documentation précise que les
   contrôles in-process ne sont pas une frontière de confinement suffisante. La frontière réelle doit
   être OS/container/VM (DeepBl4nder : workers isolés).
4. **Mémoire long terme** : via l'extra `nooa-memory`, à activer au besoin.
5. **`import nooa` charge litellm** : coût d'import non négligeable, à garder en tête pour le serveur HTTP.

## Conséquence pour DeepBl4nder

- Les agents DeepBl4nder sont des **sous-classes de `nooa.Agent`** (jamais de `GenericAgentRuntime`).
- Le contexte, les événements, la mémoire et le tracing utilisent **les API NOOA**.
- DeepBl4nder n'ajoute que le **domaine de production** : objets métier, Blender, workers, artifacts,
  QA, budgets, provenance, politiques de sécurité.
