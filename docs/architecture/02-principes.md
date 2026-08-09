# 02 — Principes fondamentaux et matrice de responsabilité

> Consolidation de : Roadmap A §2/§4/§26-27, B §2-3/§24, C §2-5/§40-41.

## Principes

**P1 — Agent = objet Python.** L'agent possède état, méthodes, contrats, capacités et
contexte : `class BlenderAgent(Agent): scene: Scene; async def build_scene(self, spec) -> Scene`.

**P2 — `...` = raisonnement agentique.** Un corps `...` est complété par une boucle LLM.
**P3 — corps Python = déterminisme.** `def frame_count(duration, fps): return round(duration*fps)`.
**P4 — Python est le langage de composition.** Objets vivants + interfaces typées + Python,
plutôt qu'une forêt de micro-tools.
**P5 — NOOA avant toute abstraction propriétaire.**

```
NOOA sait-il déjà le faire ?  → oui → utiliser NOOA
                               → non → est-ce une responsabilité du domaine audiovisuel ?
                                        → oui → DeepBlender
                                        → non → ne pas ajouter
```

## Matrice de responsabilité (résumé)

| Capacité | NOOA | DeepBlender |
|---|---:|---:|
| Runtime agentique, objet-agent, état, contexte, événements | **Natif** | Utilise |
| Typed I/O, live objects, code-as-action, stratégies, tracing | **Natif** | Utilise |
| Skills (mécanisme), MCP, sandbox, évaluation, mémoire | **Natif** | Utilise |
| Mémoire long terme | **Natif** (`nooa-memory`) | Stocke la connaissance métier comme objets métier si besoin |
| Blender, workers, scheduler de rendu | — | **DeepBlender** |
| Assets, artifacts, provenance, graphes de production | — | **DeepBlender** |
| QA métier, budgets, politiques de sécurité | — | **DeepBlender** |
| Approbations humaines | — | **DeepBlender** |

## Ce qui ne doit PAS être créé

Sauf nécessité démontrée : `GenericAgentRuntime`, `GenericAgentLoop`, `GenericContextManager`,
`GenericMemoryManager`, `GenericEventBus`, `GenericStateManager`, `GenericLLMOrchestrator`,
`GenericWorkflowEngine`, `GenericHandoffEngine`, `GenericTracingSystem`.

Avant de créer l'un de ces composants : 1) vérifier NOOA, 2) lire l'exemple, 3) lire le code
source, 4) tester l'API, 5) seulement ensuite décider.

## Ce qui DOIT rester DeepBlender

Domaine de production, domaine Blender, production state, artifact registry, provenance de
production, graphes de production, scheduling de rendu, workers Blender, cycle de vie des
assets, pipeline audio, compositing, localisation, budgets, approbations humaines, QA de
production, politiques de sécurité de production.

## Ce qu'il faut éviter

- **Un agent par micro-compétence** (`CameraAgent`, `LightingAgent`…) : préférer un
  `BlenderAgent` avec des skills `cinematography`, `lighting`, `composition`.
- **Reconstruire les services NOOA** : context manager, memory manager, agent loop,
  infrastructure d'événements, observabilité de base.
- **Exécuter directement le code généré** : `exec(llm_output)` est interdit. Pipeline :
  AST → politique → worker.
- **Laisser le LLM contrôler seul le runtime** : le LLM raisonne ; le runtime garde
  sécurité, scheduling, ressources, retries, timeouts, workers, checkpoints, budgets.

## Règle d'or

> **« Est-ce que NOOA sait déjà faire cela ? »** Si oui → utiliser NOOA. Sinon → est-ce une
> responsabilité du domaine audiovisuel ? Si oui → l'ajouter à DeepBlender. Sinon → ne pas ajouter.
