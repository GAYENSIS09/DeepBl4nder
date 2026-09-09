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
│   └── sfx.py        # SoundDesignerAgent
├── production/       # PipelineRunner, BudgetTracker, EventLog
├── llm/              # Routeur LLM cloud multi-fournisseurs (litellm)
│   ├── interface.py         # UnifiedLLM / build_llm() — interface NOOA
│   └── __init__.py          # build_llm() — routeur partagé
├── domain/           # Modèles métier typés (Brief, SceneSpec, etc.)
├── bridges/          # Ponts moteurs (blender)
├── artifacts/        # ArtifactRegistry, ProvenanceGraph
├── plugins/          # KnowledgeGraph, RenderFarm
├── codegen/          # Validateur AST scripts Blender
├── skills/           # 32 skills embarqués
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

## Routeur LLM

Le module `DeepBl4nder.llm` fournit un routeur cloud multi-fournisseurs :

| Module | Rôle |
|--------|------|
| `interface.py` | `UnifiedLLM` / `build_llm()` — interface NOOA |
| `__init__.py` | `build_llm()` — routeur partagé (litellm) |

Le routeur agrège 5 fournisseurs cloud : Gemini, Groq, NVIDIA, OpenRouter, Cloudflare.
Au moins une clé API est requise. Deux modes de routage :
- **fallback** (défaut) : basculement sur erreur.
- **vote** (via `DeepBl4nder_LLM_MODE`) : tous les fournisseurs sains votent.

### Utilisation

```python
from DeepBl4nder.llm import build_llm

llm = build_llm()
result = await llm.acall(messages=[...])
```

### Configuration

Les clés API sont définies dans `.env` : `GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `CLOUDFLARE_API_KEY` + `CLOUDFLARE_ACCOUNT_ID`.

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

## Architecture

L'ancien module `DeepBl4nder/api/` (FastAPI, JWT, RBAC, PostgreSQL, Redis, MinIO, Langfuse) a été **supprimé**. L'architecture est maintenant :

- **TUI** : Lance le pipeline in-process via `tui/embedded_api.py`
- **LLM** : Routeur cloud multi-fournisseurs via `litellm` (Gemini, Groq, NVIDIA, OpenRouter, Cloudflare)
- **Docker** : `docker compose up -d` → Blender worker

Plus de serveur HTTP, plus de base de données, plus d'authentification. Au moins une clé API LLM est requise.

## Déploiement Docker

```bash
# Core
docker compose up -d

# TUI
docker compose --profile tui up -d
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