---
name: music
description: Composer ou sélectionner la musique : thème, tempo, intensité, cohérence émotionnelle.
---

# Musique

Soutenir la dramaturgie par la musique. La musique est l'outil émotionnel le plus puissant : elle crée l'atmosphère, guide les émotions, et marque le rythme.

## Principes fondamentaux

- **La musique sert l'image** : elle ne doit pas la dominer.
- **Moins c'est plus** : un motif simple répété est plus mémorable qu'une symphonie complexe.
- **Ducking** : la musique baisse quand un personnage parle.

## Ton et émotion

| Émotion | Tonalité | Tempo | Instrumentation |
|---------|----------|-------|-----------------|
| **Joie** | Majeur | 120-140 BPM | Piano, cordes, vents légers |
| **Tristesse** | Mineur | 60-80 BPM | Piano solo, cordes douces |
| **Tension** | Chromatique | 80-100 BPM | Cordes dissonantes, percussions |
| **Action** | Majeur/Mineur | 140-180 BPM | Percussions, cuivres, électronique |
| **Mystère** | Mineur | 70-90 BPM | Synthétiseurs, cloches, silences |
| **Romance** | Majeur | 90-110 BPM | Piano, cordes, guitare acoustique |
| **Horreur** | Chromatique | 50-70 BPM | Clusters, bruits, silences |

## Structure musicale

### Pour un plan de 10 s
```
[0-2s]  Introduction  — Thème principal (motif court)
[2-5s]  Développement — Évolution du thème
[5-8s]  Climax        — Intensité maximale
[8-10s] Résolution    — Retour au calme ou fondu
```

### Pour une séquence de 1-3 min
```
[Introduction]  0-15%    — Thème principal, établir l'ambiance
[Développement] 15-50%   — Variation, montée progressive
[Climax]        50-75%   — Intensité maximale
[Résolution]    75-100%  — Retour au calme, conclusion
```

## Patterns musicaux

### Boucle (loop)
```python
# Boucle de 4 mesures (16 beats)
bpm = 120
beats_per_measure = 4
measures = 4
duration_seconds = (beats_per_measure * measures) * 60 / bpm
# = 16 * 60 / 120 = 8 secondes
```

### Hit point
- **Hit** : accent musical sur un événement visuel (impact, révélation).
- **Hit point** : moment précis où la musique "tape".
- Syncroniser avec l'action : pas avant, pas après.

### Fade in / Fade out
```python
# Fade in sur 2 secondes
# Fade out sur 3 secondes
# Volume : 0 → 1 (fade in), 1 → 0 (fade out)
```

## Mixage

### Niveaux de volume

| Piste | Volume relatif | Raison |
|-------|---------------|--------|
| **Dialogue** | 0 dB (référence) | Priorité absolue |
| **Musique** | -12 à -6 dB | Soutien, pas de compétition |
| **Ambiance** | -18 à -12 dB | Fond, atmosphère |
| **Effets** | -12 à -6 dB | ponctuation |

### Ducking (réduction automatique)
```python
# Quand le dialogue est présent, la musique baisse
# Sidechain compression : le signal dialogue réduit le volume musique
# Ratio typique : 4:1 à 8:1
# Attack : 10-50 ms
# Release : 100-500 ms
```

## Sélection de musique

### Critères
- **Cohérence émotionnelle** : la musique doit correspondre au mood.
- **Durée** : la boucle doit couvrir la durée du plan (ou plus).
- **Tempo** : doit correspondre au rythme de l'action.
- **Instrumentation** : doit être cohérente avec le monde (moderne = électronique, historique = orchestral).

### Sources
- Bibliothèque interne (assets/audio/music/)
- Génération procédurale (si disponible)
- Composition originale (via LLM + instruments virtuels)

## Sortie attendue

```python
audio_plan = {
    "type": "music",
    "mood": "warm, intimate",
    "tempo": 90,  # BPM
    "key": "C major",
    "instruments": ["piano", "strings"],
    "duration": 10.0,  # secondes
    "structure": [
        {"time": 0, "event": "fade_in", "duration": 2},
        {"time": 2, "event": "theme_a"},
        {"time": 6, "event": "theme_b", "intensity": "climax"},
        {"time": 8, "event": "fade_out", "duration": 2}
    ],
    "volume": -10,  # dB
    "ducking": True
}
```

## Erreurs courantes

1. **Musique trop forte** : le dialogue est couvert.
2. **Pas de ducking** : la musique et le dialogue se battent.
3. **Boucle pas synchronisée** : la musique "décroche" à la boucle.
4. **Mauvaise tonalité** : joie pour une scène triste, ou inversement.
5. **Trop de changements** : la musique change constamment = distraction.
6. **Oublier le silence** : parfois, pas de musique est plus fort que de la musique.

## Règles

- Associer tonalité, tempo et instrumentation à l'intention de la scène.
- Évoluer avec le récit : thèmes pour personnages, montée d'intensité maîtrisée.
- Éviter de couvrir le dialogue : bande étroite ou ducking automatique.
- Livrer des boucles/hitpoints alignés sur les beats de la séquence.
- Sortir une `AudioPlan` musique (thème, tempo, moments forts, volume).
- Prévoir les versions (musique seule / sous voix / mix complet).
