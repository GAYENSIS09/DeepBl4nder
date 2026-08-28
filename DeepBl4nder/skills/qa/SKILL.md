---
name: qa
description: Contrôles de qualité technique, visuel, continuité et sémantique.
---

# QA de production

Vérifier les artifacts produits par la production. Le QA est la dernière ligne de défense avant la livraison.

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
    return {"passed": False, "issues": ["Pas d'image rendue"]}

# Vérifier la résolution
if img.size[0] < 1920 or img.size[1] < 1080:
    return {"passed": False, "issues": ["Résolution insuffisante"]}

# Vérifier que l'image n'est pas noire
pixels = list(img.pixels)
avg_brightness = sum(pixels[:len(pixels)//4]) / (len(pixels)//4)
if avg_brightness < 0.01:
    return {"passed": False, "issues": ["Image noire"]}
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

### Scoring

```python
qa_report = {
    "technical_score": 0.0-1.0,  # 0 = échec, 1 = parfait
    "visual_score": 0.0-1.0,
    "semantic_score": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "issues": [
        {
            "type": "technical|visual|semantic",
            "severity": "critical|major|minor",
            "description": "...",
            "step_affected": "render|compositing|...",
            "recommendation": "..."
        }
    ],
    "passed": True  # overall_score > 0.7
}
```

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

## Rapport de QA

```python
{
    "overall_score": 0.85,
    "technical_score": 0.95,
    "visual_score": 0.80,
    "semantic_score": 0.80,
    "passed": True,
    "issues": [
        {
            "type": "visual",
            "severity": "minor",
            "description": "Légère sous-exposition dans le plan 3",
            "step_affected": "render",
            "recommendation": "Augmenter l'exposure de 0.3"
        }
    ],
    "recommendations": [
        "Vérifier la synchro audio sur le plan 5",
        "Ajouter un léger bloom pour la cohérence"
    ]
}
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
2. **Pas de scoring** : impossible de comparer les versions.
3. **Oublier l'audio** : le son est 50% de l'expérience.
4. **Pas de recommandations** : le rapport dit "échec" sans dire comment corriger.
5. **QA unique** : ne faire qu'un seul contrôle au lieu de la hiérarchie complète.

## Règles

- Appliquer d'abord les contrôles techniques déterministes.
- Comparer sémantiquement le brief et le rendu.
- Pointer l'étape affectée en cas d'échec pour une révision ciblée.
- Produire toujours un `QAReport` typé (score, issues, recommandations).
- Hiérarchiser : technique > visuel > sémantique.
- Toujours inclure des recommandations de correction.
