---
name: texturing
description: Créer et appliquer les textures : albedo, roughness, normal, maps selon les besoins.
---

# Texturing

Produire des textures cohérentes avec le look voulu.

## Règles

- Couvrir les maps utiles : base color, roughness, normal, height selon le matériau.
- Bakes : préférer des textures procédurales déterministes (seed fixe) reproductibles.
- Respecter la résolution cible et le budget mémoire du pipeline.
- Tester le rendu d'un échantillon avant d'engager le look complet.
- Référencer les textures par chemin relatif et hash (provenance).
- Livrer un `TextureSet` typé : maps, résolution, chemins, hash.
