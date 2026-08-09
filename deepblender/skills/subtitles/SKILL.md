---
name: subtitles
description: Produire des sous-titres synchronisés, lisibles et conformes aux formats standard.
---

# Sous-titres

Écrire et générer des sous-titres corrects.

## Règles

- Format standard : SRT / VTT / TTML selon la cible d'export.
- Synchronisation stricte sur les timestamps des plans (début/fin en secondes).
- Lisibilité : 1-2 lignes, ~15-20 caractères/seconde, pas de chevauchement.
- Ponctuation et casse cohérentes ; ne pas dupliquer ce qui est déjà audible si requis.
- Multi-langues : un fichier par langue, nommage `subtitle/<lang>/<version>`.
- Valider la synchro (aucun blanc injustifié, aucun dépassement de fin de plan).
