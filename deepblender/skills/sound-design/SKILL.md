---
name: sound-design
description: Concevoir l'ambiance sonore : fond, événements, hiérarchie, cohérence avec l'image.
---

# Sound Design

Construire la bande-son d'ambiance et d'événements.

## Règles

- Hiérarchiser : ambiances (fond), effets (événements), gros plans (émotion).
- Synchroniser les effets aux images clés (impacts, portes, pluie).
- Éviter les artefacts : niveaux cohérents, pas de clip, espace stéréo maîtrisé.
- Utiliser des sources reproductibles (boucles seedées, synthèse déterministe).
- Laisser la place au dialogue et à la musique (ducking).
- Sortir un `AudioPlan` (mood, pistes, timing) puis un mix intégré au `AudioMaster`.
