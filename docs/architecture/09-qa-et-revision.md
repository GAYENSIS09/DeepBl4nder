# 09 — QA et boucle de révision

> Consolidation de : Roadmap A §22, B §15-16, C §12/§31.

## Niveaux de QA

- **Technique** : `.blend` valide, assets présents, références valides, FPS/résolution
  corrects, render terminé.
- **Visuel** : personnage visible, composition, éclairage cohérent, caméra, animation présente.
- **Continuité** : personnage/costume/décor cohérents, relations avec les plans précédents.
- **Sémantique** : comparaison `Brief ↔ Render` (ex. « le rendu contient bien une ruelle et un
  personnage, mais l'ambiance lumineuse ne correspond pas au brief »).

Résultat typé :

```python
class QAReport:
    passed: bool
    score: float
    issues: list[Issue]
    recommendations: list[str]
```

## Boucle de correction (cœur du système)

```text
Render → QA → PASS → Artifact
            └─ FAIL → Diagnosis → RevisionSpec → BlenderAgent → nouvelle exécution
```

La révision retourne à **l'étape concernée** (problème caméra → CameraAgent → Layout →
Pre-render), jamais à toute la production.

Exemples de transitions :
- `Camera QA failure → CameraAgent → Layout/Camera → Pre-render`
- `Rig failure → RiggingAgent → Animation → Pre-render`

L'agent doit pouvoir **observer le résultat et corriger**, pas seulement produire une première réponse.

