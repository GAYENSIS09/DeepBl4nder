---
name: modeling
description: Créer et modifier la géométrie Blender : primitives, extrusion, boucles, topologie propre.
---

# Modeling

Créer des assets 3D avec une topologie propre, en bpy déterministe.

## Règles

- Démarrer de primitives ; opérer par extrude/inset/loop cut pour garder des quads.
- Garder une topologie propre : quads dominants, éviter les n-gones et triangles visibles.
- Centrer et orienter l'objet sur l'origine ; appliquer la scale avant export.
- Nommer objets et collections explicitement (`obj_<asset>_<purpose>`).
- Vérifier la scale (échelle réaliste) et la norme (Y-up / Z-up selon pipeline).
- Sortir un `AssetSpec` + code bpy réutilisable ; jamais de mesh généré par `exec`.
