---
name: shading
description: Construire les matériaux et le look dev : PBR, valeurs physiques, cohérence de scène.
---

# Shading

Configurer les matériaux pour un rendu physique et cohérent.

## Règles

- Base PBR : base color, roughness, metalness dans des plages réalistes.
- Éviter les valeurs extrêmes (base color > 1, roughness 0 partout).
- Relier les maps aux nœuds (texture coordinate → mapping → image texture).
- Utiliser la lumière pour valider le matériau (test sur une sphère de référence).
- Cohérence : un même matériau = même nœud/group réutilisé (asset de material).
- Livrer un `MaterialSpec` typé et un LookDev d'évaluation.
