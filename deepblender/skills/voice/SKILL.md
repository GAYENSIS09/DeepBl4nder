---
name: voice
description: Doubler les personnages : casting vocal, direction, diction, accents, synchronisation.
---

# Voix

Porter les dialogues : crédibilité, accents, diction et synchro. La voix est le lien direct entre le personnage et le spectateur.

## Principes fondamentaux

- **Crédibilité** : la voix doit correspondre au personnage (âge, origine, émotion).
- **Clarté** : le dialogue doit être compréhensible, même en sous-titre.
- **Émotion** : la voix porte l'émotion plus que les mots.

## Casting vocal

### Profils vocaux

| Type | Caractéristiques | Usage |
|------|------------------|-------|
| **Soprano** | Aigu, léger | Enfants, fées, personnages jeunes |
| **Alto** | Moyen, chaleureux | Personnages féminins adultes |
| **Ténor** | Moyen-aigu, vif | Personnages masculins jeunes |
| **Baryton** | Moyen-grave, riche | Personnages masculins adultes |
| **Basse** | Grave, profond | Autorité, menace, sagesse |

### Directions de casting

```python
voice_profile = {
    "speaker": "hero",
    "age": "30-35",
    "gender": "male",
    "tone": "warm, confident",
    "accent": "neutral",
    "register": "casual",
    "pace": "moderate"
}
```

## Direction d'acteur

### Émotion par ligne

```python
directions = [
    {
        "line": "Je suis venu pour le café.",
        "emotion": "calme, déterminé",
        "pace": "moderate",
        "volume": "normal",
        "note": "Pas d'agressif, juste factuel"
    },
    {
        "line": "C'est le meilleur que j'ai goûté.",
        "emotion": "sincère, émerveillé",
        "pace": "lent",
        "volume": "doux",
        "note": "Laisser un silence avant la ligne"
    }
]
```

### Types d'émotion

| Émotion | Direction | Exemple |
|---------|-----------|---------|
| **Joie** | Sourire dans la voix, débit rapide | "C'est génial !" |
| **Tristesse** | Voix basse, débit lent, pauses | "Je ne sais pas..." |
| **Colère** | Volume élevé, débit rapide, tranchant | "C'est inacceptable !" |
| **Peur** | Voix haute, tremblante, hésitations | "Qu'est-ce que... ?" |
| **Surprise** | Accent montant, pause avant | "Ah ! Vraiment ?" |
| **Neutre** | Débit régulier, pas d'exagération | "Le café est prêt." |

## Synchronisation labiale (lip-sync)

### Contraintes

```python
# Durée de la ligne = durée du plan
line_duration = 3.0  # secondes
line_text = "Le café est prêt."
char_count = len(line_text)  # 18 caractères
chars_per_second = char_count / line_duration  # 6 cps

# Pour les sous-titres : 15-20 cps
# Pour la voix : 5-8 cps (plus lent)
```

### Timing

- **Début** : la bouche s'ouvre 0.1-0.2 s avant le son.
- **Fin** : la bouche se ferme 0.1-0.2 s après le son.
- **Pauses** : les silences sont aussi importants que les mots.

## Multi-langues

### Contraintes

```python
# Même performance, langues différentes
versions = {
    "fr": {"text": "Le café est prêt.", "duration": 2.5},
    "en": {"text": "The coffee is ready.", "duration": 2.3},
    "es": {"text": "El café está listo.", "duration": 2.6},
    "de": {"text": "Der Kaffee ist fertig.", "duration": 2.8}
}
```

### Durées par langue
- **Français** : 5-7 cps
- **Anglais** : 6-8 cps
- **Espagnol** : 5-7 cps
- **Allemand** : 4-6 cps (plus longs mots composés)

## Traitement audio

### Niveaux

```python
# Niveaux de voix
voice_level = 0  # dB (référence)
noise_floor = -60  # dB (bruit de fond)
headroom = 6  # dB (marge avant clipping)
```

### Traitements

| Traitement | Usage | Paramètre |
|------------|-------|-----------|
| **Compression** | Niveaux constants | Ratio 3:1, attack 10ms, release 100ms |
| **EQ** | Clarté | Boost 2-5 kHz, cut < 100 Hz |
| **Dé-essing** | Réduire les sibilances | Seuil 4-6 kHz |
| **Noise gate** | Supprimer le bruit | Seuil -40 dB |

## Sortie attendue

```python
voice_pass = {
    "speaker": "hero",
    "language": "fr",
    "lines": [
        {
            "text": "Le café est prêt.",
            "start": 0.5,
            "end": 2.5,
            "emotion": "calme",
            "file": "hero_line_01.wav"
        }
    ],
    "total_duration": 3.0,
    "sample_rate": 44100,
    "bit_depth": 16
}
```

## Erreurs courantes

1. **Voix hors sync** : la voix ne correspond pas aux lèvres.
2. **Niveaux inconstants** : certaines lignes trop fortes, d'autres trop faibles.
3. **Pas de dé-essing** : sibilances ("s") agressives.
4. **Émotion incohérente** : la voix ne correspond pas à la scène.
5. **Trop rapide** : le dialogue est incompréhensible.
6. **Oublier les pauses** : le dialogue est un flux continu sans respiration.

## Règles

- Adapter le registre, l'accent et la diction au personnage et au format.
- Direction : indiquer intentions (émotion, débit, pauses) par réplique.
- Synchroniser la voix aux lèvres/durées du plan (timestamps).
- Niveaux constants, dé-essé propres, pas de clip.
- Gérer plusieurs langues : mêmes performances, sync subtitles + lips.
- Sortir un `VoicePass` typé (locuteur, timing, chemins, langue).
