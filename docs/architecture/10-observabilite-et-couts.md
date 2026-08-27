# 10 — Observabilité, budgets et reprise après crash

> Consolidation de : Roadmap A §9, C §18-19/§35.

## Observabilité (deux plans reliés, pas remplacés)

```text
NOOA observability          DeepBl4nder observability
  agent / LLM / code          production / workers / renders
  context / methods           artifacts / coûts
  events / strategies         budgets / retries / failures
```

Métriques : latence, tokens, coût LLM, coût render, temps worker, utilisation GPU, retries,
échecs, score QA, nombre d'artifacts, budget.

Reliés par les **identifiants de corrélation** (`production_run_id`, `agent_run_id`, `event_id`, …).

## Budget et coûts

Chaque `ProductionRun` suit : coût LLM, coût render, coût storage, coût API externe, total,
budget, budget restant.

```text
Budget: 1.00 € → LLM 0.18 € + Render 0.46 € + Audio 0.08 € + Storage 0.02 € = 0.74 €
```

Le système doit interrompre ou demander une validation quand une politique de budget l'exige.
Objectif : alerte de dépassement < 30 s.

## Reprise après crash

Une production interrompue doit reprendre sans perte :

```text
ProductionRun → événements persistants → checkpoint/state → crash → restart
  → récupérer le travail non consommé → replay/resume
```

- NOOA fournit une partie des primitives de runtime/event sourcing ;
- DeepBl4nder garantit la **persistance et la reprise de l'état de production** :
  journal d'événements append-only (JSONL) + `ProductionRun.recover` qui rejoue
  les événements non consommés (étapes démarrées sans événement terminal) ;
- les artifacts déjà validés ne sont **pas recréés** inutilement.

## Temps réel

La gateway expose l'état et les coûts en temps réel :
- `/budget` : état du `BudgetTracker` (total, budget, restant, `over_budget`) ;
- `/events` : flux SSE sur le bus ; `BudgetTracker` publie une alerte dès le
  franchissement du budget (objectif < 30 s).
