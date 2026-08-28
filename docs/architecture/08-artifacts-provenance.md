# 08 — Artifacts, provenance et graphes

> Consolidation de : Roadmap A §19-21, B §12-14, C §21-23.

## Artifact

Un artifact est un résultat concret ou une unité de production identifiable :
`Brief`, `SceneSpec`, `ShotSpec`, `Storyboard`, script Python, `.blend`, render, audio,
vidéo, `QAReport`, manifest.

Chaque artifact porte : `id`, `type`, `version`, `hash`, `parents`, `creator`, `agent_run`,
`production_run`, `skill_versions`, `model`, `parameters`, `timestamps`, `cost`, `status`.

## Cycle de vie

```text
SPEC → GENERATED → VALIDATED → EXECUTED → CREATED → INSPECTED → QA
  ├── REJECTED → REVISION → NEW VERSION
  └── APPROVED → PUBLISHED
```

## Provenance

Répond à la question : **« Pourquoi cet artifact existe-t-il ? »**

```text
Artifact → Production step → Shot → Agent Run → trace NOOA → Context → Memory
  → Skill → Code/Tool → Worker → Input artifacts
```

Exemple : `render_v002.png → scene_v002.blend → scene_v002.py → ShotSpec → SceneSpec
→ BlenderAgent → NOOA/LLM → Skills`.

La provenance permet reproductibilité, comparaison de versions, rollback, audit, analyse des
coûts, diagnostic.

## Graphes

Trois graphes distincts, relationnels (pas un moteur d'exécution imposé) :

- **Dependency graph** : `Asset → Scene → Shot → Render` — « si cet asset change, quels
  artifacts faut-il recalculer ? »
- **Provenance graph** : `Brief → Spec → AgentRun → Code → Blend → Render`.
- **Knowledge graph** (optionnel) : `Character appears_in → Shot`, `interacts_with → Asset` —
  utile pour continuité, recherche, dépendances.

À terme : convergence vers un **Production Knowledge Graph**.

