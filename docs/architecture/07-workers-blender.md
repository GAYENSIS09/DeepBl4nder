# 07 — Workers Blender, génération de code et sécurité

> Consolidation de : Roadmap A §11/§17, B §9-10/§20, C §13-14/§29.

## Pipeline du code généré

```text
Agent → Python généré → validation NOOA → politique DeepBl4nder → sandbox → worker → Blender
```

Le code généré **n'est jamais exécuté directement** (`exec(llm_output)` interdit) :

```text
Generated Python → AST parsing → validation statique → politique → sandbox/worker → Blender
```

Contrôles : imports autorisés, accès fichiers, `subprocess`, réseau, chemins, opérations
destructives, ressources, durée d'exécution.

**Objectif : aucun code généré ne sort du périmètre autorisé.**

## Blender Worker

Blender est isolé du processus principal.

```text
NOOA Agent → DeepBl4nder capability → Blender plugin → Worker Manager
  → Blender Worker → Blender process
```

Avantages : isolation, récupération après crash, contrôle CPU/GPU, timeouts, parallélisation,
plusieurs scènes simultanées. Cible : `Worker 1 → Scene A`, `Worker 2 → Scene B`, `Worker 3 → Scene C`,
ajout dynamique d'un worker sans redémarrage (implémenté : `WorkerScheduler.add_workers`).

Le worker possède : `worker_id`, `GPU`, `scene`, `process`, `environment`, `timeout`,
`status`, `artifacts`, `logs`.

Le scheduler (local / worker pool / render farm) appartient à DeepBl4nder.

## Sécurité

Principes : moindre privilège, isolation de Blender, validation du code généré, chemins
contrôlés, réseau limité, ressources limitées, opérations destructives contrôlées, aucune
opération interdite silencieuse.

Exemple de politique :

```text
BlenderAgent : read_scene ALLOW, modify_scene ALLOW, render ALLOW, save ALLOW,
               shell DENY, arbitrary_network DENY
```

Le LLM raisonne ; le runtime garde la sécurité, le scheduling, les ressources, les retries,
les timeouts, les workers, les checkpoints et les budgets.
