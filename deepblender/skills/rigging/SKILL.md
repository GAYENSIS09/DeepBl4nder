---
name: rigging
description: Créer et valider les rigs : armatures, poids, contraintes, contrôleurs.
---

# Rigging

Rigger personnages et objets pour une animation prévisible.

## Règles

- Chaîne propre : armature → bones avec hiérarchie lisible (hips, spine, chest, head…).
- Weight painting : éviter les influences croisées excessives (max ~4 groupes/os).
- Ajouter des contrôleurs (IK/FK) uniquement quand le besoin est explicite.
- Valider : pose par défaut stable, aucune déformation cassée, scale de bone correcte.
- Livrer un `RigSpec` + `WeightReport` et une `PoseLibrary` de base.
- Enregistrer le rig comme asset versionné avec son poids (weight painting) vérifié.
