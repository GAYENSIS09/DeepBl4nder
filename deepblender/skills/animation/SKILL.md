---
name: animation
description: Animation simple et déterministe (mouvement, rotation, keyframes).
---

# Animation

Animer des objets de façon déterministe dans Blender.

## Règles

- Utiliser des keyframes explicites sur des frames calculées (`frame_count`).
- Animer le strict nécessaire pour le plan (5-10 s).
- Produire une `AnimationSpec` typée avant le script bpy.
