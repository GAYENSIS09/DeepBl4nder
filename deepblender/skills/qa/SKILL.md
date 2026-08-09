---
name: qa
description: Contrôles de qualité technique, visuel, continuité et sémantique.
---

# QA de production

Vérifier les artifacts produits par la production.

## Règles

- Appliquer d'abord les contrôles techniques déterministes.
- Comparer sémantiquement le brief et le rendu.
- Pointer l'étape affectée en cas d'échec pour une révision ciblée.
- Produire toujours un `QAReport` typé (score, issues, recommandations).
