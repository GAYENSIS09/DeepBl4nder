---
name: feasibility
description: Étudier la faisabilité technique d'une idée : durée, complexité, ressources, budget, risques.
---

# Faisabilité

Évaluer si une intention est réalisable avec un délai et des ressources donnés.

## Règles

- Décomposer en étapes du pipeline (préproduction → export).
- Estimer : durée, complexité, assets requis, besoin GPU, coût LLM/render.
- Identifier les risques (assets manquants, simulations coûteuses, rig complexe).
- Proposer des simplifications si le brief dépasse les contraintes.
- Sortir un `FeasibilityReport` typé : verdict, estimation, contraintes, alternatives.
- Réviser le plan (durée, complexité, périmètre) si les contraintes sont dépassées.
