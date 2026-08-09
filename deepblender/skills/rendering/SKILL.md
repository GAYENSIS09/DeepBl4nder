---
name: rendering
description: Paramétrer et lancer le rendu : engine, samples, format, color management, budget GPU.
---

# Rendu

Produire des images de qualité dans un budget de temps et de GPU maîtrisé.

## Règles

- Choisir l'engine (Cycles qualité / Eevee vitesse) selon le besoin.
- Échantillonnage adapté : démarrer bas pour les tests, augmenter pour le final.
- Color management : fixer view transform (AgX / Filmic) et white balance.
- Format de sortie explicite (PNG/EXR, résolution, framerate, codec).
- Budget : estimer le coût de rendu par frame et vérifier le budget du run.
- Lancer via le worker ; lire le résultat, vérifier l'image produite avant QA.
