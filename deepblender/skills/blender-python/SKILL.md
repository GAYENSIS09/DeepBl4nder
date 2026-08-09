---
name: blender-python
description: Générer et manipuler des scènes Blender de façon sûre et déterministe avec bpy.
---

# Blender Python

Utiliser `bpy` pour créer et modifier des scènes Blender déterministes.

## Règles

- Préférer des scripts reproductibles (seed fixe, setup explicite).
- Inspecter avant toute opération destructive.
- Garder l'organisation de la scène explicite (collections, noms).
- N'exécuter jamais de commande système arbitraire.
- Se limiter aux imports autorisés : `bpy`, `math`, `mathutils`, `random`, `json`.
