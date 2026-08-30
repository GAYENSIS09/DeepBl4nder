# Guide du développeur — DeepBl4nder

Ce guide décrit comment contribuer au paquet `DeepBl4nder`. L'architecture est détaillée dans [`docs/architecture/`](architecture/README.md).

## Structure du paquet

```text
DeepBl4nder/
├── agents/           # 14 agents NOOA + factory
│   ├── base.py       # BaseAgent avec context management
│   ├── factory.py    # build_agents() - source unique
│   ├── story.py      # StoryAgent
│   ├── storyboard.py # StoryboardAgent
│   ├── director.py   # DirectorAgent
│   ├── blender.py    # BlenderAgent
│   ├── qa.py         # QAAgent
│   ├── audio.py      # AudioAgent
│   ├── animator.py   # AnimatorAgent
│   ├── char.py       # CharacterDesignerAgent
│   ├── comp.py       # CompositingAgent
│   ├── env.py        # EnvironmentArtistAgent
│   ├── loc.py        # LocalizationAgent
│   ├── music.py      # MusicComposerAgent
│   ├── review.py     # ReviewAgent
│   ├── sfx.py        # SoundDesignerAgent
│   ├── ue5.py        # UE5Agent
│   ├── godot.py      # GodotAgent
│   └── ai_video.py   # AIVideoAgent
├── production/       # PipelineRunner, BudgetTracker, EventLog
├── llm/              # Système LLM local
│   ├── model_registry.py    # Spécs modèles Qwen3
│   ├── classifier.py        # Classification tâches
│   ├── cascade.py           # Router cascade (1.5B→4B→8B)
│   ├── server.py            # Serveur llama-cpp-python
│   ├── client.py            # Client HTTP
│   ├── interface.py         # LLMClient unifié
│   └── download.py          # Téléchargeur GGUF
├── domain/           # Modèles métier typés (Brief, SceneSpec, etc.)
├── bridges/          # Ponts moteurs (blender, ue5, godot, ai_video)
├── artifacts/        # ArtifactRegistry, ProvenanceGraph
├── plugins/          # KnowledgeGraph, RenderFarm
├── codegen/          # Validateur AST scripts Blender
├── skills/           # 26 skills embarqués
├── tui/              # Interface terminal Textual
├── cli.py            # Point d'entrée CLI
└── tests/            # Suite de tests
```

## Règle de séparation NOOA ↔ domaine

- **Les agents** héritent de `nooa.Agent` : méthodes `async def ...` = capacités agentiques, corps Python normal = logique déterministe.
- **Le domaine, codegen, artifacts, production, bridges, LLM, TUI n'importent JAMAIS `nooa`** : testé par `tests/test_decoupling.py`.
- NOOA n'est encapsulé que derrière les agents et le mécanisme de skills.

> Si un besoin ressemble à `GenericAgentRuntime`, `GenericEventBus`, etc. : c'est que NOOA sait déjà le faire — utiliser NOOA (voir `architecture/02-principes.md`).

## Ajouter un agent

1. Créer `DeepBl4nder/agents/mon_agent.py` :
   ```python
   from nooa import Agent

   class MonAgent(Agent):
       """You are … (docstring = prompt système)."""

       def helper_deterministe(self, x: int) -> int:
           return x * 2

       async def action_agentique(self, spec: MySpec) -> MyResult:
           """Description de l'action."""
           ...
   ```

2. Exporter dans `DeepBl4nder/agents/__init__.py`.

3. Ajouter dans `DeepBl4nder/agents/factory.py` :
   ```python
   from DeepBl4nder.agents.mon_agent import MonAgent

   def build_agents() -> tuple[...]:
       ...
       return (
           ...,
           MonAgent(llm=llm),
       )
   ```

4. Ajouter un test dans `tests/test_decoupling.py` (sous-classe de `nooa.Agent`, méthode agentique en coroutine, corps déterministes purs).

5. L'instanciation en test nécessite un LLM : `FakeLLMClient()` de NOOA.

## Factory d'agents centralisée

`agents.factory.build_agents()` est la **seule source de vérité** pour créer la crew. Elle est utilisée par :
- Le TUI (`tui/embedded_api.py`)
- Les tests
- Tout consommateur externe

```python
from DeepBl4nder.agents.factory import build_agents

story, storyboard, director, blender, qa, ... = build_agents()
```

## Ajouter un skill

1. Créer `DeepBl4nder/skills/<nom>/SKILL.md` avec frontmatter `name:` / `description:` puis les règles. `SkillRegistry` le découvre automatiquement ; `TextSkill` (NOOA) gère le chargement.
2. La description est injectée à bas coût (progressive disclosure) ; le contenu complet n'est chargé qu'à la résolution.

## Ajouter un objet métier

Créer un dataclass typé dans `DeepBl4nder/domain/`, l'exporter dans `__init__.py`, et l'utiliser comme type de retour d'une capacité agentique (contrat de sortie).

## Système LLM Local

Le module `DeepBl4nder.llm` fournit un système complet :

| Module | Rôle |
|--------|------|
| `model_registry.py` | Registre modèles Qwen3 (1.5B, 4B, 8B GGUF) |
| `classifier.py` | Classification heuristique tâches (mots-clés) |
| `cascade.py` | Router cascade : 1.5B → 4B → 8B |
| `server.py` | Serveur llama-cpp-python (GPU) |
| `client.py` | Client HTTP compatible OpenAI |
| `interface.py` | `LLMClient` / `build_llm()` pour agents |
| `download.py` | Téléchargeur GGUF depuis HuggingFace |

### Routage en cascade

```python
from DeepBl4nder.llm import build_llm

client = build_llm()
result = await client.acall(messages=[...])  # Auto-select + escalade
```

Le routeur :
1. Classifie la tâche (CODING, REASONING, GENERAL, FAST)
2. Sélectionne le modèle le plus léger capable
3. En cas d'échec/qualité insuffisante → escalade au modèle suivant

### Télécharger les modèles

```bash
python -m DeepBl4nder.llm.download --all
```

## Exécuter un script Blender

```python
from DeepBl4nder.bridges.blender.bridge import BlenderBridge
from DeepBl4nder.domain.scene import BlenderScript

bridge = BlenderBridge()                     # Binaire via BLENDER_EXE
result = bridge.run_script(script, workdir)  # blender -b -P <script>
```

Le script doit d'abord passer `ASTValidator` (imports autorisés, pas de `exec`/`eval`/`subprocess`/`os.system`, pas d'accès réseau).

## BaseAgent — Context Management

Tous les agents héritent de `BaseAgent` qui fournit :

- `_load_schema_context(modules)` — Injection schéma KG sémantique
- `_init_context_management()` — Pruner + Cache
- `_load_core_skills()` — Skills avec troncature
- `_get_cache_metrics()` — Métriques cache

```python
class MonAgent(BaseAgent):
    async def plan(self, brief: Brief) -> Plan:
        await self._load_schema_context("narrative", "scene")
        # Le contexte est injecté automatiquement
        ...
```

## Tests

```bash
# Lint + Type check
ruff check DeepBl4nder tests
mypy DeepBl4nder tests

# Tests
pytest
pytest tests/test_decoupling.py -q  # Découplage NOOA ↔ domaine
```

## Architecture sans API

L'ancien module `DeepBl4nder/api/` (FastAPI, JWT, RBAC, PostgreSQL, Redis, MinIO, Langfuse) a été **supprimé**. L'architecture est maintenant :

- **TUI** : Lance le pipeline in-process via `tui/embedded_api.py`
- **LLM** : Serveur local `llama.cpp` sur port 8080
- **Docker** : `docker compose up -d` → LLM + Blender worker

Plus de serveur HTTP, plus de base de données, plus d'authentification.

## Déploiement Docker

```bash
# Core
docker compose up -d

# Profils optionnels
docker compose --profile ue5 up -d
docker compose --profile godot up -d
docker compose --profile ai-video up -d
```

## Vérifications

```bash
ruff check DeepBl4nder tests
mypy DeepBl4nder tests
pytest
pytest tests/test_decoupling.py -q
```

## Contribution

1. Fork & branch
2. Code + tests
3. `ruff check --fix && mypy && pytest`
4. PR avec description claire