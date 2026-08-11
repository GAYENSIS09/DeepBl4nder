---
name: subtitles
description: Produire des sous-titres synchronisés, lisibles et conformes aux formats standard.
---

# Sous-titres

Écrire et générer des sous-titres corrects. Les sous-titres sont le lien entre l'audio et le spectateur.

## Formats supportés

| Format | Extension | Usage |
|--------|-----------|-------|
| **SRT** | .srt | Standard universel, simple |
| **VTT** | .vtt | Web (HTML5) |
| **TTML** | .ttml | Broadcast, TV |
| **STL** | .stl | Télévision numérique |

## Structure SRT

```
1
00:00:01,000 --> 00:00:03,500
Le café est prêt.

2
00:00:04,000 --> 00:00:06,000
C'est du Sumatra.

3
00:00:07,000 --> 00:00:09,500
Torréfaction locale.
```

## Contraintes de lisibilité

### Nombre de caractères

| Paramètre | Valeur | Raison |
|-----------|--------|--------|
| **Max par ligne** | 42 caractères | Lisibilité à l'écran |
| **Max par sous-titre** | 2 lignes | Pas de bloc de texte |
| **Max par seconde** | 20 caractères | Rythme de lecture |
| **Durée min** | 1 seconde | Temps de lecture |
| **Durée max** | 7 secondes | Pas d'oubli |

### Calcul du timing

```python
def calculate_subtitle_duration(text, chars_per_second=15):
    """Calculer la durée minimale d'un sous-titre."""
    char_count = len(text)
    min_duration = char_count / chars_per_second
    return max(min_duration, 1.0)  # minimum 1 seconde
```

## Synchronisation

### Timing

```python
# Les timestamps doivent correspondre à l'audio
subtitle = {
    "index": 1,
    "start": "00:00:01,000",
    "end": "00:00:03,500",
    "text": "Le café est prêt.",
    "speaker": "barista"
}
```

### Règles de sync

- **Début** : 0.1-0.2 s avant le début de la parole.
- **Fin** : 0.1-0.2 s après la fin de la parole.
- **Pas de chevauchement** : un seul sous-titre à la fois.
- **Pas de blanc injustifié** : les silences ne doivent pas avoir de sous-titre.

## Ponctuation et casse

### Ponctuation

- **Point** : fin de phrase.
- **Virgule** : pause courte.
- **Points de suspension** : hésitation, non-dit.
- **Point d'interrogation** : question.
- **Point d'exclamation** : émotion forte.

### Casse

- **Majuscule** : début de phrase, noms propres.
- **Minuscule** : reste.
- **PAS DE CAPS LOCK** : sauf emphasis exceptionnelle.

## Multi-langues

### Nommage des fichiers

```
subtitles/
├── fr/
│   ├── subtitles_v1.srt
│   └── subtitles_v2.srt
├── en/
│   ├── subtitles_v1.srt
│   └── subtitles_v2.srt
└── es/
    └── subtitles_v1.srt
```

### Traduction

- Traduire l'intention, pas mot à mot.
- Adapter la longueur à la durée du plan.
- Garder la cohérence des noms propres.

## Validation

```python
def validate_srt(srt_content):
    """Valider un fichier SRT."""
    issues = []
    
    # Vérifier la numérotation
    lines = srt_content.strip().split('\n')
    index = 1
    for i, line in enumerate(lines):
        if line.strip().isdigit():
            if int(line.strip()) != index:
                issues.append(f"Numérotation incorrecte à la ligne {i+1}")
            index += 1
    
    # Vérifier les timestamps
    for i, line in enumerate(lines):
        if '-->' in line:
            start, end = line.split('-->')
            # Vérifier le format HH:MM:SS,mmm
            if not validate_timestamp(start.strip()):
                issues.append(f"Timestamp invalide à la ligne {i+1}")
    
    return issues
```

## Génération automatique

```python
# Générer des sous-titres à partir d'un DialogueSpec
subtitles = []
for dialogue in scene.dialogue:
    subtitle = {
        "index": len(subtitles) + 1,
        "start": format_time(dialogue.start),
        "end": format_time(dialogue.end),
        "text": dialogue.text,
        "speaker": dialogue.speaker
    }
    subtitles.append(subtitle)
```

## Erreurs courantes

1. **Pas de sync** : les sous-titres ne correspondent pas à l'audio.
2. **Trop de texte** : le spectateur ne peut pas lire.
3. **Chevauchement** : deux sous-titres en même temps.
4. **Mauvaise ponctuation** : phrases incompréhensibles.
5. **Oublier le speaker** : en multi-locuteur, ne pas indiquer qui parle.
6. **Format incorrect** : SRT mal formé = erreur de lecture.

## Règles

- Format standard : SRT / VTT / TTML selon la cible d'export.
- Synchronisation stricte sur les timestamps des plans (début/fin en secondes).
- Lisibilité : 1-2 lignes, ~15-20 caractères/seconde, pas de chevauchement.
- Ponctuation et casse cohérentes ; ne pas dupliquer ce qui est déjà audible si requis.
- Multi-langues : un fichier par langue, nommage `subtitle/<lang>/<version>`.
- Valider la synchro (aucun blanc injustifié, aucun dépassement de fin de plan).
