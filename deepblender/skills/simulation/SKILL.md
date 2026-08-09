---
name: simulation
description: Ajouter des simulations physiques : fluides, tissus, cheveux, particules, contraintes.
---

# Simulation

Utiliser les simulations Blender quand la physique compte.

## Règles

- Ne simuler que si nécessaire (fluide, tissu, cheveux, soft body) ; sinon animer à la main.
- Cache la simulation : la précalculer et la figer avant le render final.
- Seed fixe et paramètres déterministes pour la reproductibilité.
- Budget : réduire la résolution de simulation pour les tests, augmenter au final.
- Vérifier la stabilité (pas de blow-up) avant de lancer le render.
- Livrer un `SimulationCache` versionné rattaché à l'`AnimatedScene`.
