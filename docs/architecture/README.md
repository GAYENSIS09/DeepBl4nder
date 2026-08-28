# DeepBl4nder — Architecture (source de vérité)

> **Statut :** consolidation active.
> Les trois feuilles de route préliminaires (`docs/roadmaps/DeepBl4nder_Architecture_NOOA_A/B/C.md`)
> sont **archivées** et ne doivent plus évoluer. Ce dossier est la source de vérité unique,
> alignée sur les capacités **réellement disponibles** de NOOA 0.0.8 (voir `00-nooa.md`).

## Ce que DeepBl4nder est

DeepBl4nder est une plateforme de **production audiovisuelle assistée par agents IA**,
construite **au-dessus de NOOA** (NVIDIA NeMo Labs OO-Agents, arXiv:2607.20709).

```
                USER
                  │
                  ▼
         DeepBl4nder (domaine de production + Blender + artifacts + QA)
                  │
                  ▼
      NOOA (runtime agentique : objet = agent, contexte, événements,
            mémoire, stratégies, code-as-action, tracing, skills, MCP)
                  │
   ┌──────────────┼──────────────┐
   ▼              ▼              ▼
Blender       Audio/FFmpeg    Assets/Storage
   │              │              │
   └───────┬──────┴──────┬───────┘
           ▼             ▼
      Workers        Artifacts
```

**La règle d'or** : DeepBl4nder n'est *pas* « un framework d'agents qui utilise NOOA » ;
c'est une *plateforme de production audiovisuelle dont le runtime agentique est NOOA*.
Toute capacité déjà fournie par NOOA est utilisée, jamais réimplémentée.

## Décision de consolidation (ADR-001)

| Sujet | Choix retenu | Source dominante |
|---|---|---|
| Responsabilités NOOA / DeepBl4nder | Matrice de responsabilité (§ `02-principes.md`) | Roadmap A §4, C §4-5 |
| Distinction Agent Run / Production Run | Corrélés mais séparés (§ `04-agents.md`) | Roadmap C §6-7 |
| Lifecycles & transitions | Lifecycles Agent / Production + 32 transitions | Roadmap C §25-34 |
| Identité de corrélation | `project_id` … `worker_id`, coûts, timestamps | Roadmap C §7 |
| Objets métier | Objets Python vivants typés (pas de DTO figés) | Roadmap A §5-6 |
| Code généré | Pipeline AST → policy → worker (jamais `exec` direct) | Roadmap B §10, C §14 |
| QA | Technique / visuel / continuité / sémantique + boucle révision ciblée | Roadmap B §15-16 |
| Budgets & observabilité | Budget par ProductionRun, alertes < 30 s | Roadmap C §19 |
| Architecture dossiers | Layout finalisé (§ `11-roadmap.md`) | Roadmap C §39 |
| Skills | Paquets de connaissance `SKILL.md` + progressive disclosure | Roadmap B §6, C §9 |
| Roadmap d'implémentation | Phases 0→7, verticale Blender d'abord | Roadmap C §44 |

## Documents

| Document | Contenu |
|---|---|
| [`00-nooa.md`](00-nooa.md) | **Matrice de capacités NOOA 0.0.8 réelle** (signatures, fichiers, limites) |
| [`01-contexte-et-objectifs.md`](01-contexte-et-objectifs.md) | Vision, objectifs, métriques, cas d'usage, portée initiale |
| [`02-principes.md`](02-principes.md) | Principes fondamentaux, règle NOOA-first, matrice de responsabilité, ce qu'il ne faut PAS créer |
| [`03-domaine-production.md`](03-domaine-production.md) | Objets métier, specs structurées, pipeline audiovisuel en 18 étapes |
| [`04-agents.md`](04-agents.md) | Agents, Agent Run vs Production Run, transitions, collaboration, human-in-the-loop |
| [`05-skills.md`](05-skills.md) | Skills : catalogue, structure, progressive disclosure |
| [`06-tools-et-plugins.md`](06-tools-et-plugins.md) | Tools (actions) et plugins (frontières externes) |
| [`07-workers-blender.md`](07-workers-blender.md) | Workers Blender, bridge, scheduler, génération de code et sécurité |
| [`08-artifacts-provenance.md`](08-artifacts-provenance.md) | Artifacts, versioning, provenance, graphes |
| [`09-qa-et-revision.md`](09-qa-et-revision.md) | QA multi-niveaux et boucle de révision ciblée |
| [`10-observabilite-et-couts.md`](10-observabilite-et-couts.md) | Observabilité, budgets, reprise après crash |
| [`11-roadmap.md`](11-roadmap.md) | Roadmap d'implémentation et architecture des dossiers |

## État d'avancement

| Élément | Statut |
|---|---|
| Consolidation théorique | Fait (ce dossier) |
| Paquet Python `DeepBl4nder/` | Fait (domain, agents NOOA, 26 skills, blender, codegen, plugins+tools, production, api, cli) |
| Tests (`tests/`, dont `test_decoupling.py`) | Fait (95 tests verts) |
| CI (ruff, mypy, pytest) | Fait — lint, typecheck et tests passent localement |
| Docker / docker-compose | Configurés (Dockerfile corrigé : install avec NOOA) ; image non construite |
| Verticale Blender (render réel) | Code fait ; render à valider dans l'image Docker (Blender absent de l'hôte) |

## Lecture conseillée

1. `01-contexte-et-objectifs.md` — pourquoi
2. `02-principes.md` — comment penser l'architecture
3. `00-nooa.md` — sur quoi on s'appuie
4. `04-agents.md`, `07-workers-blender.md`, `09-qa-et-revision.md` — le cœur du système
5. `11-roadmap.md` — par quoi commencer

