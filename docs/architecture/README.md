# DeepBl4nder — Architecture (Source de vérité)

> **Statut :** Architecture consolidée (août 2026)
> DeepBl4nder utilise un **routeur LLM cloud multi-fournisseurs** (via `litellm`) et Blender 4.1+ pour le rendu 3D.
> Ce dossier est la source de vérité unique pour l'architecture actuelle.

## Ce que DeepBl4nder est

DeepBl4nder est une plateforme de **production audiovisuelle** assistée par agents IA, construite **au-dessus de NOOA 0.0.8**.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (TUI Terminal)                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    14 AGENTS NOOA (In-Process)                      │
│  Story │ Storyboard │ Director │ Character │ Environment          │
│  Blender │ QA │ Audio │ Compositing │ Localization │ Review       │
│  Animator │ Music │ Sound Design                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              CLOUD LLM ROUTER (litellm, UnifiedLLM)                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Gemini │ Groq │ NVIDIA │ OpenRouter │ Cloudflare           │   │
│  │  Mode: fallback (défaut) ou vote (DeepBl4nder_LLM_MODE)     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        ┌──────────┐
                        │ Blender  │
                        │ Worker   │
                        │ (Docker) │
                        └──────────┘
```

**Règle d'or** : DeepBl4nder est une **plateforme de production audiovisuelle** dont le runtime agentique est NOOA. Toute capacité fournie par NOOA est utilisée, jamais réimplémentée. Au moins une clé API LLM est requise pour le fonctionnement.

## Décisions Architecturales (ADR)

| ADR | Sujet | Choix | Raison |
|-----|-------|-------|--------|
| ADR-001 | Architecture | TUI in-process | Simplicité, pas de dépendances cloud lourdes |
| ADR-002 | LLM | litellm multi-fournisseur (Gemini, Groq, NVIDIA, OpenRouter, Cloudflare) | Haute disponibilité, pas de dépendance unique, pas de modèle local |
| ADR-003 | Routage LLM | Fallback (défaut) ou vote | Résilience, tolerance d'erreur par provider |
| ADR-004 | Interface | TUI (Textual) | Développeur-first, live stream, pas de navigateur |
| ADR-005 | Déploiement | Docker Compose simple | `docker compose up -d` — Blender worker |
| ADR-006 | Agents | Factory centralisée | `agents.factory.build_agents()` source unique |
| ADR-007 | Contexte | KG sémantique + Vector Store | RAG pour injection schéma domain |

## Architecture des Dossiers

```
DeepBl4nder/
├── agents/               # 14 agents NOOA + factory
│   ├── base.py           # BaseAgent (context mgmt, skills, cache)
│   ├── factory.py        # build_agents() — SEULE source de vérité
│   ├── story.py          # StoryAgent
│   ├── storyboard.py     # StoryboardAgent
│   ├── director.py       # DirectorAgent
│   ├── blender.py        # BlenderAgent
│   ├── qa.py             # QAAgent
│   ├── audio.py          # AudioAgent
│   ├── animator.py       # AnimatorAgent
│   ├── char.py           # CharacterDesignerAgent
│   ├── comp.py           # CompositingAgent
│   ├── env.py            # EnvironmentArtistAgent
│   ├── loc.py            # LocalizationAgent
│   ├── music.py          # MusicComposerAgent
│   ├── review.py         # ReviewAgent
│   └── sfx.py            # SoundDesignerAgent
├── production/           # PipelineRunner, BudgetTracker, EventLog
├── llm/                  # Routeur LLM cloud multi-fournisseurs (litellm)
│   ├── interface.py         # UnifiedLLM / build_llm() — interface NOOA
│   └── __init__.py          # build_llm() — routeur partagé
├── domain/               # Modèles métier typés (dataclasses)
│   ├── narrative.py      # StorySpec, Act, StoryBeat, DialogueLine, Storyboard*
│   ├── scene.py          # SceneSpec, ShotSpec, CharacterSpec, CameraSpec...
│   ├── media.py          # AudioPlan, CompositeSpec, AnimationResult...
│   ├── qa.py             # QAReport, QAIssue
│   ├── project.py        # Brief, Project, Production
│   └── schema_*.py       # Bootstrap KG + Vector Store
├── bridges/              # Ponts vers moteurs externes
│   └── blender/          # BlenderBridge (bpy headless)
├── artifacts/            # ArtifactRegistry + ProvenanceGraph
├── plugins/              # KnowledgeGraph, RenderFarm
├── codegen/              # ASTValidator (sécurité scripts Blender)
├── skills/               # 32 skills embarqués (SKILL.md)
├── tui/                  # Interface Terminal (Textual)
│   ├── app.py            # App principale
│   ├── embedded_api.py   # Pipeline in-process
│   ├── event_bridge.py   # Flux live événements agents
│   ├── widgets/          # AgentStream, StatusBar, TaskBar
│   └── screens/          # Console, Library, Settings
├── cli.py                # CLI entry point
└── tests/                # Tests (decoupling, etc.)
```

## Supprimé (Ancienne architecture SaaS)

| Composant | Remplacé par |
|-----------|--------------|
| `DeepBl4nder/api/` (FastAPI, JWT, RBAC) | ❌ Supprimé — TUI in-process |
| PostgreSQL | ❌ Supprimé — Fichiers locaux (`data/runs/`) |
| Redis | ❌ Supprimé — Pas de cache/queue distribué |
| MinIO | ❌ Supprimé — Stockage local |
| Langfuse | ❌ Supprimé — Observabilité locale (logs) |
| Frontend Next.js | ❌ Supprimé — TUI Textual |
| Auth/JWT | ❌ Supprimé — Pas d'auth multi-tenant |

## Documents

| Document | Contenu |
|----------|---------|
| [`00-nooa.md`](00-nooa.md) | Capacités NOOA 0.0.8 réelles |
| [`01-contexte-et-objectifs.md`](01-contexte-et-objectifs.md) | Vision, objectifs, métriques |
| [`02-principes.md`](02-principes.md) | Principes, règle NOOA-first, matrice responsabilité |
| [`03-domaine-production.md`](03-domaine-production.md) | Objets métier, specs, pipeline 18 étapes |
| [`04-agents.md`](04-agents.md) | 14 agents, Agent Run vs Production Run |
| [`05-skills.md`](05-skills.md) | Skills, progressive disclosure |
| [`06-tools-et-plugins.md`](06-tools-et-plugins.md) | Tools, plugins, ponts externes |
| [`07-workers-blender.md`](07-workers-blender.md) | Workers Blender, bridge, codegen, sécurité |
| [`08-artifacts-provenance.md`](08-artifacts-provenance.md) | Artifacts, versioning, provenance |
| [`09-qa-et-revision.md`](09-qa-et-revision.md) | QA multi-niveaux, boucle révision |
| [`10-observabilite-et-couts.md`](10-observabilite-et-couts.md) | Budgets, observabilité, crash recovery |
| [`11-roadmap.md`](11-roadmap.md) | Roadmap et architecture dossiers |

## Lecture conseillée

1. `00-nooa.md` — Capacités NOOA 0.0.8
2. `02-principes.md` — Comment penser l'architecture
3. `04-agents.md` — 14 agents, collaboration
4. `07-workers-blender.md` — Workers, codegen, sécurité
5. `09-qa-et-revision.md` — QA + boucle révision
6. Module `DeepBl4nder/llm/` — Routeur LLM cloud multi-fournisseurs