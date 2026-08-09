---
name: compositing
description: Assembler les passes de rendu : correction, profondeur, effets, étalonnage final.
---

# Compositing

Assembler le rendu en une image finale maîtrisée.

## Règles

- Utiliser les passes (diffuse, direct, shadow, mist, depth) pour un contrôle précis.
- Travailler en EXR/PBR avant de dégrader en 8-bit pour l'export.
- Correction : balance, contraste, teinte par couche (shadows/midtones/highlights).
- Effets ciblés : bloom, DOF, vignette — avec modération et intention.
- Étalonnage final cohérent entre les plans d'une même séquence.
- Sortir un `CompositeArtifact` versionné relié à son `RenderArtifact`.
