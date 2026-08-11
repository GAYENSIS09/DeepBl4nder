---
name: sound-design
description: Concevoir l'ambiance sonore : fond, événements, hiérarchie, cohérence avec l'image.
---

# Sound Design

Construire la bande-son d'ambiance et d'événements. Le sound design crée l'immersion sonore et renforce la narration.

## Hiérarchie sonore

```
Niveau 1 : Dialogue         (priorité absolue)
Niveau 2 : Effets (événements)  (ponctuation)
Niveau 3 : Ambiance (fond)     (immersion)
Niveau 4 : Musique           (émotion)
```

- **Règle** : chaque niveau ne doit pas couvrir les niveaux supérieurs.
- **Ducking** : quand le dialogue est présent, les autres niveaux baissent.

## Ambiance (fond)

### Types d'ambiance

| Type | Exemple | Niveau |
|------|---------|--------|
| **Intérieur calme** | Bureau, chambre | -24 dB |
| **Intérieur animé** | Café, restaurant | -18 dB |
| **Extérieur calme** | Forêt, jardin | -20 dB |
| **Extérieur urbain** | Rue, parc | -16 dB |
| **Extérieur nature** | Plage, montagne | -18 dB |

### Boucles d'ambiance
```python
# Boucle d'ambiance de 30 secondes
# Fade in : 2 secondes
# Fade out : 3 secondes
# Volume : -18 dB (référence)
```

## Effets (événements)

### Types d'effets

| Type | Exemple | Durée | Niveau |
|------|---------|-------|--------|
| **Impact** | Coup, chute, explosion | 0.1-0.5 s | -6 dB |
| **Action** | Pas, portes, objets | 0.5-2 s | -12 dB |
| **Réaction** | Soupir, rire, cri | 0.5-3 s | -10 dB |
| **Détail** | Papier, clés, tissu | 0.1-1 s | -18 dB |

### Synchronisation
```python
# Les effets doivent être synchronisés avec l'image
# Frame exacte de l'événement visuel
event_frame = 120  # frame de l'impact
event_time = event_frame / fps  # en secondes
```

## Couches sonores

### Structure d'une scène
```
Couche 1 : Ambiance (loop continu)
Couche 2 : Effets d'action (syncro image)
Couche 3 : Effets de détail (texture sonore)
Couche 4 : Musique (émotion)
```

### Exemple : scène dans un café
```
Ambiance : bruit de fond de café (conversations lointaines, machine à café)
Effets action : tasse posée, cuillère qui tourne
Effets détail : papier qui froisse, chaise qui glisse
Musique : jazz doux en fond
```

## Niveaux et mixage

### Niveaux de référence

| Source | Niveau | Panning |
|--------|--------|---------|
| Dialogue | 0 dB | Centre |
| Effets proches | -6 dB | Selon position |
| Effets lointains | -18 dB | Large |
| Ambiance | -18 à -12 dB | Stéréo large |
| Musique | -12 à -6 dB | Stéréo |

### Panning (positionnement stéréo)
```python
# Gauche = -1.0, Centre = 0.0, Droite = 1.0
# Un objet à gauche de l'écran → panning à gauche
# Un objet qui traverse → panning qui suit le mouvement
```

## Sources reproductibles

### Boucles seedées
```python
# Utiliser des boucles avec un seed fixe pour la reproductibilité
# La même seed = le même résultat sonore
seed = 42
```

### Synthèse déterministe
```python
# Bruis, tonalités générées par code
# Pas de dépendance à des fichiers audio externes
```

## Patterns courants

### Ambiance extérieure
```
Fond : vent, oiseaux lointains
Effets : pas sur gravier, portes qui claquent
Détail : feuilles qui bougent, insectes
```

### Ambiance intérieure
```
Fond : HVAC, conversations lointaines
Effets : pas, objets posés
Détail : tissu, papier, horloge
```

### Scène d'action
```
Fond : musique intense
Effets : impacts, coups, débris
Détail : respiration, pas rapides
```

## Sortie attendue

```python
audio_plan = {
    "type": "sound_design",
    "layers": [
        {
            "name": "ambiance",
            "source": "cafe_ambiance_loop.wav",
            "volume": -18,
            "fade_in": 2,
            "fade_out": 3
        },
        {
            "name": "effects",
            "events": [
                {"time": 2.5, "source": "cup_place.wav", "volume": -12},
                {"time": 5.0, "source": "spoon_stir.wav", "volume": -15}
            ]
        }
    ],
    "ducking": True,
    "master_volume": -12
}
```

## Erreurs courantes

1. **Pas de hiérarchie** : tous les sons au même niveau = confusion.
2. **Ambiance trop forte** : le dialogue est couvert.
3. **Effets non synchronisés** : le son ne correspond pas à l'image.
4. **Pas de stereo** : tout au centre = plat, pas d'immersion.
5. **Boucles qui "clipent"** : le début et la fin de la boucle ne s'enchaînent pas.
6. **Oublier le silence** : parfois, le silence est plus fort que le bruit.

## Règles

- Hiérarchiser : ambiances (fond), effets (événements), gros plans (émotion).
- Synchroniser les effets aux images clés (impacts, portes, pluie).
- Éviter les artefacts : niveaux cohérents, pas de clip, espace stéréo maîtrisé.
- Utiliser des sources reproductibles (boucles seedées, synthèse déterministe).
- Laisser la place au dialogue et à la musique (ducking).
- Sortir un `AudioPlan` (mood, pistes, timing) puis un mix intégré au `AudioMaster`.
