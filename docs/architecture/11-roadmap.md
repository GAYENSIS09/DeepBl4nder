# 11 — Roadmap d'implémentation et architecture des dossiers

> Consolidation de : Roadmap A §25/§34, B §5/§23, C §39/§42-44.

## Architecture des dossiers (finale)

```text
deepblender/
├── pyproject.toml
├── README.md
├── Dockerfile
├── docker-compose.yml
├── docs/
│   ├── architecture/          ← source de vérité (ce dossier)
│   └── roadmaps/              ← archives, ne pas faire évoluer
├── deepblender/               ← paquet Python
│   ├── __init__.py
│   ├── cli.py                 ← point d'entrée `deepblender`
│   ├── agents/                ← sous-classes nooa.Agent (director, blender, qa)
│   ├── domain/                ← objets métier typés (project, scene, shot, asset, qa)
│   ├── skills/                ← registry/loader (mécanique NOOA : TextSkill)
│   ├── blender/               ← bridge, worker, scheduler
│   ├── codegen/               ← blender_python, validator (AST), policy
│   ├── artifacts/             ← registry, versioning, provenance
│   ├── production/            ← runs, scheduler, budget, recovery
│   ├── bridge/                ← worker process (frontière isolée)
│   └── api/                   ← serveur HTTP minimal (+ web/static)
├── skills/                    ← contenu métier des skills (SKILL.md)
├── tests/                     ← unit + decoupling + integration
└── projects/                  ← projets / exemples
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

## Ordre de priorité

La priorité n'est pas « écrire beaucoup de code » mais :
**étudier NOOA → mapper ses capacités → les intégrer → construire uniquement les briques
métier manquantes → valider avec une verticale Blender → étendre progressivement.**
