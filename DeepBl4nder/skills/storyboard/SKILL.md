---
name: storyboard
description: Décomposer une scène en plans (Storyboard, ShotPlan).
---

# Storyboard

Transformer une narration en découpage technique. Le storyboard est la traduction du récit en langage cinématographique.

## Types de plans

| Plan | Focale | Durée | Fonction |
|------|--------|-------|----------|
| **Plan large (ELS)** | 24-35mm | 3-5 s | Établir le lieu, montrer le contexte |
| **Plan moyen (MS)** | 50mm | 3-5 s | Action, dialogue, interactions |
| **Plan rapproché (CU)** | 85-135mm | 2-4 s | Émotion, réaction, détail |
| **Plan très rapproché (ECU)** | 100-200mm | 1-2 s | Détail significatif, tension |
| **Plan d'ensemble (WS)** | 24mm | 4-6 s | Personnage dans son environnement |
| **Plan de coupe (Cutaway)** | Variable | 1-2 s | Réaction, détail, transition |

## Découpage standard (plan de 10 s)

```
[0-2s]  Plan large    — Établir le lieu, l'ambiance
[2-5s]  Plan moyen    — Montrer l'action principale
[5-7s]  Plan rapproché — Émotion/réaction
[7-9s]  Plan moyen    — Action qui conclut
[9-10s] Plan large    — Résolution, transition
```

## Structure d'un ShotSpec

```python
{
    "shot_id": "shot_01",
    "duration": 3.5,  # secondes
    "type": "medium",
    "camera": {
        "focal": 50,
        "position": [0, -5, 1.7],
        "rotation": [90, 0, 0],
        "movement": "static"  # ou "pan_left", "dolly_in", etc.
    },
    "action": "Le barista verse le café dans la tasse",
    "emotion": "concentration, précision",
    "audio": "bruit du café qui coule, musique en fond",
    "transition_next": "cut"  # ou "dissolve", "fade"
}
```

## Règles de découpage

### Règle des 180°
- Imaginer une ligne droite entre les deux sujets.
- La caméra reste toujours du même côté de cette ligne.
- Changement de côté = confusion pour le spectateur.

### Règle de la continuité
- Le regard du personnage doit avoir une direction cohérente.
- Les objets en main doivent être cohérents entre plans.
- La lumière vient du même côté.

### Montage alterné
- Montrer A, puis B, puis A → créer de la tension.
- Utile pour les conversations, les parallèles.

### Raccord
- **Sur l'action** : couper pendant le mouvement (plus fluide).
- **Avant l'action** : couper avant la fin du mouvement (dynamique).
- **Après l'action** : couper après la fin du mouvement (lent, contemplatif).

## Shotlist pour plan de 10 s

```python
shots = [
    {
        "shot_id": "s01",
        "duration": 2.0,
        "type": "wide",
        "focal": 28,
        "movement": "static",
        "action": "Établir le café, ambiance matinale"
    },
    {
        "shot_id": "s02",
        "duration": 3.0,
        "type": "medium",
        "focal": 50,
        "movement": "dolly_in_slow",
        "action": "Le barista prépare le café"
    },
    {
        "shot_id": "s03",
        "duration": 2.0,
        "type": "close-up",
        "focal": 85,
        "movement": "static",
        "action": "Les mains versent le café (détail)"
    },
    {
        "shot_id": "s04",
        "duration": 2.0,
        "type": "medium",
        "focal": 50,
        "movement": "pan_right",
        "action": "Le client reçoit la tasse, sourit"
    },
    {
        "shot_id": "s05",
        "duration": 1.0,
        "type": "wide",
        "focal": 35,
        "movement": "dolly_out",
        "action": "Vue globale du café, transition"
    }
]
```

## Erreurs courantes

1. **Tous les plans à la même focale** : pas de variation = monotone.
2. **Pas de plan de coupe** : impossible de monter proprement.
3. **Plans trop longs** : ennui. Alterner les durées.
4. **Plans trop courts** : confusion. Minimum 1-2 s par plan.
5. **Pas de justification** : chaque plan doit avoir une raison d'exister.
6. **Oublier l'audio** : le son est 50% de l'expérience.

## Règles

- Découper en plans compréhensibles, 5-10 s chacun.
- Justifier chaque plan (information, émotion, action).
- Varier les focales et les cadrages pour la dynamique.
- Respecter la règle des 180° et la continuité.
- Prévoir des plans de coupe pour le montage.
- Produire une liste de `ShotSpec` typées, jamais du bpy brut.
- Chaque shot a un objectif émotionnel clair.
