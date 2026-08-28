---
name: continuity
description: Garantir la continuité entre les plans : costumes, lumière, position, props, raccords.
---

# Continuité

Éviter les ruptures visibles entre plans adjacents. La continuité est invisible quand elle fonctionne, mais très visible quand elle casse.

## Types de continuité

### 1. spatiale
- **Position** : les objets et personnages sont au même endroit.
- **Direction** : le personnage regarde dans la même direction.
- **Distance** : la distance entre les personnages est cohérente.

### 2. Temporelle
- **Heure** : la lumière correspond à l'heure de la journée.
- **Durée** : le temps écoulé est cohérent.
- **Saison** : les éléments saisonniers sont cohérents.

### 3. Visuelle
- **Costume** : mêmes vêtements, mêmes accessoires.
- **Maquillage** : identique d'un plan à l'autre.
- **Props** : objets au même endroit, même état.

### 4. Lumière
- **Direction** : la lumière vient du même côté.
- **Couleur** : température de couleur constante.
- **Intensité** : même niveau de luminosité.

### 5. Audio
- **Ambiance** : même bruit de fond.
- **Niveaux** : même volume de dialogue.
- **Réverbération** : même espace sonore.

## Règle des 180°

```
Personnage A ←---10 m---→ Personnage B
            (ligne d'action)

La caméra reste TOUJOURS du même côté de cette ligne.
Si elle passe de l'autre côté = confusion pour le spectateur.
```

```python
# Vérifier la règle des 180°
cam_positions = [
    (0, -5, 1.7),   # Plan 1 : caméra devant A
    (3, -5, 1.7),   # Plan 2 : caméra décalée à droite (OK)
    (0, 5, 1.7),    # Plan 3 : caméra derrière B (CASSÉ !)
]
```

## Checklist de continuité

### Par plan

```python
continuity_check = {
    "spatial": {
        "character_positions": True,
        "prop_positions": True,
        "gaze_direction": True
    },
    "temporal": {
        "light_consistency": True,
        "time_of_day": True,
        "duration_plausibility": True
    },
    "visual": {
        "costume_match": True,
        "makeup_match": True,
        "prop_state": True
    },
    "lighting": {
        "direction": True,
        "color_temperature": True,
        "intensity": True
    },
    "audio": {
        "ambiance_match": True,
        "volume_consistency": True,
        "reverb_match": True
    }
}
```

## Comparaison side-by-side

```python
# Pour comparer deux plans adjacents
# 1. Capturer un frame de chaque plan
# 2. Les côte à côte
# 3. Vérifier les points de continuité
```

### Points de vérification

| Élément | Plan A | Plan B | Cohérent ? |
|---------|--------|--------|------------|
| Position personnage | (2, 0, 0) | (2.1, 0, 0) | ✅ (écart < 0.1) |
| Direction regard | +X | +X | ✅ |
| Costume | rouge | rouge | ✅ |
| Lumière direction | droite | droite | ✅ |
| Ambiance sonore | café | bureau | ❌ |

## Seuils d'acceptation

| Élément | Seuil | Raison |
|---------|-------|--------|
| Position | ±0.1 m | Mouvement naturel |
| Direction | ±10° | Légère variation |
| Lumière | ±10% | Pas de changement brutal |
| Volume audio | ±3 dB | Pas de saut |
| Couleur temp | ±5°K | Légère variation |

## Erreurs courantes

1. **Règle des 180° cassée** : le spectateur ne sait plus qui est où.
2. **Costume change** : le personnage porte quelque chose de différent.
3. **Lumière change** : la lumière vient d'un côté dans un plan, de l'autre dans le suivant.
4. **Props déplacés** : les objets bougent entre les plans.
5. **Ambiance sonore change** : le bruit de fond est différent.
6. **Oublier le temps** : il fait jour dans un plan, nuit dans le suivant (sans justification).

## Règles

- Raccords : positions, directions (axe 180°), gestes et objets en main.
- Lumière et température de couleur constantes entre plans d'une même scène.
- Costumes, maquillage, accessoires : identiques d'un plan à l'autre.
- Comparer les renders d'essai côté à côte avant validation.
- Signaler les écarts dans le `QAReport` (rubrique continuité) et cibler la révision.
