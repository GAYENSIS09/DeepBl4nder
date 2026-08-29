---
name: qa
description: Contrôles de qualité technique, visuel, continuité et sémantique.
---

# QA de production

Vérifier les artifacts produits par la production. Le QA est la dernière ligne de défense avant la livraison.

## Sortie obligatoire — QAReport

Vous DEVEZ appeler `return_result` avec un `QAReport` :

```python
return_result(
    passed=True,        # True si score >= 70.0, False sinon
    score=85.0,         # 0.0 (pire) à 100.0 (meilleur), 70+ = pass
    issues=[],          # liste de Issue(kind, message, step)
    recommendations=[]  # liste de suggestions d'amélioration
)
```

## Format Issue

Chaque issue DOIT cibler une étape pour la révision :

```python
Issue(kind=IssueKind.TECHNICAL, message="script has syntax error", step="blender")
Issue(kind=IssueKind.VISUAL, message="image too dark", step="blender")
Issue(kind=IssueKind.SEMANTIC, message="mood mismatch with brief", step="director")
```

Étapes valides : `"director"`, `"blender"`, `"qa"`, `"animation"`, `"compositing"`, `"localization"`

## Hiérarchie des contrôles

```
1. Technique (déterministe)    → Erreurs bloquantes
2. Visuel (semi-déterministe)  → Problèmes esthétiques
3. Sémantique (LLM)           → Incohérences narratives
```

## 1. Contrôles techniques (automatisables)

### Image

```python
import bpy

# Vérifier qu'une image existe
img = bpy.data.images.get("RenderResult")
if img is None:
    return_result(
        passed=False, score=0.0,
        issues=[Issue(kind=IssueKind.TECHNICAL, message="Pas d'image rendue", step="blender")],
        recommendations=["Vérifier les paramètres de rendu"]
    )

# Vérifier la résolution
if img.size[0] < 1920 or img.size[1] < 1080:
    issues.append(Issue(kind=IssueKind.TECHNICAL, message="Résolution insuffisante", step="blender"))

# Vérifier que l'image n'est pas noire
pixels = list(img.pixels)
avg_brightness = sum(pixels[:len(pixels)//4]) / (len(pixels)//4)
if avg_brightness < 0.01:
    issues.append(Issue(kind=IssueKind.TECHNICAL, message="Image noire", step="blender"))
```

### Script Blender

```python
# Vérifier que le script s'exécute sans erreur
# Vérifier les imports
# Vérifier que les objets existent
# Vérifier les materials assignés
```

### Audio

```python
# Vérifier que le fichier audio existe
# Vérifier la durée
# Vérifier le niveau (pas de clip)
# Vérifier la synchro avec l'image
```

## 2. Contrôles visuels

### Checklist

- [ ] **Exposition** : image ni trop sombre ni trop claire
- [ ] **Focus** : le sujet est net, l'arrière-plan est flou (si DOF)
- [ ] **Composition** : règle des tiers respectée
- [ ] **Lumière** : ombres cohérentes, pas de zones bouchées
- [ ] **Matériaux** : pas d'artefacts, couleurs réalistes
- [ ] **Continuité** : cohérence entre les plans
- [ ] **Animation** : pas de tremblements, mouvements fluides
- [ ] **Audio** : niveaux corrects, synchro OK

### Scoring (0-100)

| Score | Statut | Signification |
|-------|--------|---------------|
| 90-100 | passed=True | Excellent, prêt pour la livraison |
| 70-89 | passed=True | Bon, quelques améliorations possibles |
| 50-69 | passed=False | Moyen, révision nécessaire |
| 0-49 | passed=False | Mauvais, révision majeure nécessaire |

## 3. Contrôles sémantiques (LLM)

### Brief vs Rendu

```python
semantic_checks = [
    "Le rendu correspond-il à l'intention du brief ?",
    "Les couleurs sont-elles cohérentes avec le mood ?",
    "La composition guide-t-elle le regard correctement ?",
    "L'animation est-elle naturelle ?",
    "L'audio renforce-t-il l'émotion ?"
]
```

### Cohérence narrative

```python
narrative_checks = [
    "Chaque plan a-t-il un objectif dramatique ?",
    "Le rythme est-il respecté ?",
    "Les personnages sont-ils crédibles ?",
    "La résolution est-elle satisfaisante ?"
]
```

## Exemple de sortie complète

```python
return_result(
    passed=True,
    score=82.0,
    issues=[
        Issue(kind=IssueKind.VISUAL, message="Légère sous-exposition dans le plan 3", step="blender"),
        Issue(kind=IssueKind.TECHNICAL, message="Matériau verre non PBR", step="blender"),
    ],
    recommendations=[
        "Augmenter l'exposure de 0.3 sur le plan 3",
        "Vérifier la synchro audio sur le plan 5",
        "Ajouter un léger bloom pour la cohérence",
    ]
)
```

## Révision

### Si échec technique
- Corriger le script Blender
- Re-render
- Re-QA

### Si échec visuel
- Ajuster les paramètres (lumière, materials, caméra)
- Re-render
- Re-QA

### Si échec sémantique
- Revoir le storyboard
- Modifier le script
- Re-render
- Re-QA

## Erreurs courantes

1. **QA trop superficiel** : vérifier uniquement "ça marche" sans vérifier "c'est bien".
2. **Score toujours 0** : ne jamais retourner 0 sauf artifact complètement cassé.
3. **Oublier l'audio** : le son est 50% de l'expérience.
4. **Pas de recommandations** : le rapport dit "échec" sans dire comment corriger.
5. **QA unique** : ne faire qu'un seul contrôle au lieu de la hiérarchie complète.
6. **Issue sans step** : chaque issue DOIT cibler une étape pour la révision.

## Règles

- Appliquer d'abord les contrôles techniques déterministes.
- Comparer sémantiquement le brief et le rendu.
- Score >= 70.0 → passed=True. Score < 70.0 → passed=False.
- Pointer l'étape affectée en cas d'échec pour une révision ciblée.
- Produire toujours un `QAReport` typé via `return_result`.
- Hiérarchiser : technique > visuel > sémantique.
- Toujours inclure des recommandations de correction.
