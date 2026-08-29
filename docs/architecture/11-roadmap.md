# 11 — Roadmap d'implémentation et architecture des dossiers

> Consolidation de : Roadmap A §25/§34, B §5/§23, C §39/§42-44.
> Mise à jour post-consolidation API (ADR-002) : SaaS FastAPI + frontend Next.js intégrés.

## Architecture des dossiers (finale)

```text
DeepBl4nder/
├── pyproject.toml
├── README.md
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── architecture/          ← source de vérité (ce dossier)
│   ├── roadmaps/              ← archives, ne pas faire évoluer
│   └── cahier-de-conception-v1.md
├── DeepBl4nder/               ← paquet Python
│   ├── __init__.py
│   ├── cli.py                 ← point d'entrée `DeepBl4nder` (inspect|validate|serve|seed)
│   ├── llm.py                 ← multi-provider LLM router (vote)
│   ├── agents/                ← sous-classes nooa.Agent (director, blender, ue5, godot, ai_video, qa, audio, compositing, localization)
│   ├── domain/                ← objets métier typés (project, scene, shot, asset, qa, media)
│   ├── skills/                ← registry/loader (mécanique NOOA : TextSkill)
│   ├── bridges/               ← clients REST pour moteurs externes (blender, ue5, godot, ai_video)
│   ├── blender/               ← bridge, worker, scheduler
│   ├── codegen/               ← blender_python, validator (AST), policy
│   ├── artifacts/             ← registry, versioning, provenance
│   ├── production/            ← runs, scheduler, budget, recovery
│   ├── bridge/                ← worker process (frontière isolée)
│   ├── plugins/               ← 13 plugins (audio, blender, ue5, godot, ai-video, ffmpeg, git, storage, knowledge, asset-library, rendering, media, tools)
│   └── api/                   ← API SaaS FastAPI (auth, orgs, workspaces, projects, productions, SSE, worker, usage, validate)
├── frontend/                  ← Next.js 14 (App Router) : dashboard, pipeline, realtime, costs, members
├── tests/                     ← unit + decoupling + integration (17 suites)
└── examples/                  ← exemples et fixtures (scratch/, run_pipeline.py, run_director.py)
```

## Roadmap d'implémentation

| Phase | Contenu | Statut |
|---|---|---|
| 0 | Consolidation théorique (`docs/architecture/`) | Fait |
| 1 | Squelette installable : package, CLI, domain, agents NOOA, plugins + tools, tests | Fait |
| 2 | Verticale Blender : bridge → worker → render (headless, `BLENDER_EXE`) | Code fait ; render réel à valider dans l'image Docker (Blender absent de l'hôte) |
| 3 | Production state / artifacts / provenance / revisions / human-in-the-loop | Fait (registry, provenance, runs, approbations) |
| 4 | Recovery / observabilité / budgets | Fait (journal JSONL + replay, SSE `/events`, alerte budget, `/budget`) |
| 5 | Skills complets (catalogue 26 skills) | Fait |
| 6 | Audio / compositing / localisation | Fait (plugins audio/ffmpeg/subtitle/tts, specs média, `LanguagePackage`) |
| 7 | Industrialisation : render farm, GPU scheduling, storage, caching | Fait (scheduler CPU/GPU extensible à chaud, `RenderFarmPlugin`, `StoragePlugin`) |
| 8 | SaaS Foundation : auth/JWT, multi-tenant, RBAC 4 rôles, FastAPI, frontend Next.js | Fait |
| 9 | Vagues 0-3 : hygiène, rendu fiable, contrats de production, pipeline créatif | En cours |
| 10 | Verticale UE5 : bridge → agent → server (Lumen, Nanite, MRQ) | Fait |
| 11 | Verticale Godot : bridge → agent → server (GDScript, WebGL) | Fait |
| 12 | Verticale AI Video : bridge → agent → server (CogVideoX, SVD, AnimateDiff) | Fait |

## Ordre de priorité

La priorité n'est pas « écrire beaucoup de code » mais :
**étudier NOOA → mapper ses capacités → les intégrer → construire uniquement les briques
métier manquantes → valider avec une verticale Blender → étendre progressivement.**

## Décisions d'architecture enregistrées (ADR)

- **ADR-001** : `docs/architecture/` = source de vérité unique ; `docs/roadmaps/` archivées.
- **ADR-002** (cette session) : Consolidation API sur FastAPI `app.py` ; dépréciation `server.py` ; `docker-compose.yml` et CLI `serve` pointent vers FastAPI ; endpoint `/validate` porté.

