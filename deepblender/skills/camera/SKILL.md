---
name: camera
description: Définir cadrage, focale et mouvement de caméra au service de l'intention.
---

# Caméra

Décider où mettre la caméra et comment elle bouge.

## Règles

- Choisir la focale selon le rapport au personnage (focale ≠ zoom : perspective).
- Position et hauteur : œil, contre-plongée, plongée — chaque choix a un sens.
- Mouvement motivé : travelling, pan, handheld ; pas de mouvement gratuit.
- Coordonner avec la lumière : soleil/lampe côté caméra ou contre, avec intention.
- Sortir une `CameraSpec` (position, rotation, focale) et un `CameraPass` d'animation.
- Vérifier le cadre sur un render d'essai avant d'engager l'étape d'animation.
