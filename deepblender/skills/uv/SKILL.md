---
name: uv
description: Déplier les UV pour un texturing propre : seams, densité uniforme, pack sans chevauchement.
---

# UV Mapping

Préparer le dépliage UV avant texturing.

## Règles

- Placer les seams sur les arêtes invisibles (mâchoires, aisselles, dos).
- Uniformiser la densité texel pour éviter les étirements.
- Packer les îles sans chevauchement avec une marge suffisante.
- Respecter l'orientation des îles (projection from view pour les surfaces planes).
- Prévoir du padding (bleed) pour l'antialiasing des bords de texture.
- Sortir un `UVSpec` (map, densité, résolution cible) associé au `TextureSet`.
