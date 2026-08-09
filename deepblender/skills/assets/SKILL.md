---
name: assets
description: Gérer le cycle de vie des assets : recherche, génération, import, validation, versioning.
---

# Assets

Ordonner l'acquisition et la gestion des assets d'une production.

## Règles

- Pipeline : Search / Generate / Import → Validate → Register → Version.
- Conventions de nommage stables (`asset/<type>/<name>/<version>`).
- Valider chaque asset : polycount, scale, textures référencées, rig fonctionnel.
- Enregistrer dans le registry avec hash, provenance et dépendances.
- Versionner à chaque modification ; ne jamais écraser un asset publié.
- Types couverts : characters, props, environment, textures, HDRI, audio.
