---
name: translation
description: Traduire dialogues, sous-titres et interface en plusieurs langues avec fidélité et contexte.
---

# Traduction

Adapter le contenu à plusieurs langues sans perdre le sens ni le ton. La traduction n'est pas de la transposition mot à mot.

## Principes fondamentaux

1. **Traduire l'intention** : ce que le personnage veut dire, pas les mots exacts.
2. **Respecter le ton** : formel, familier, poétique, technique.
3. **Contraintes de longueur** : les sous-titres ont une durée fixe.
4. **Cohérence** : un terme = toujours la même traduction.

## Contraintes par langue

| Langue | CPS max | Caractères max/ligne | Notes |
|--------|---------|---------------------|-------|
| **Français** | 20 | 42 | Plus long que l'anglais |
| **Anglais** | 20 | 42 | Référence |
| **Espagnol** | 18 | 40 | 10-15% plus long que l'anglais |
| **Allemand** | 15 | 38 | Mots composés longs |
| **Chinois** | 12 | 16 | Caractères, pas de mots |
| **Japonais** | 12 | 16 | Kanji + hiragana |

## Glossaire

```python
glossary = {
    "fr": {
        "café": "café",
        "barista": "barista",
        "torréfaction": "torréfaction",
        "Sumatra": "Sumatra"
    },
    "en": {
        "café": "coffee",
        "barista": "barista",
        "torréfaction": "roasting",
        "Sumatra": "Sumatra"
    },
    "es": {
        "café": "café",
        "barista": "barista",
        "torréfaction": "tueste",
        "Sumatra": "Sumatra"
    }
}
```

### Règles de glossaire

- **Noms propres** : toujours identiques (Sumatra, pas "Sumatera").
- **Termes techniques** : vérifier l'équivalent exact.
- **Marques** : ne pas traduire.
- **Noms de personnages** : identiques toutes langues.

## Patterns de traduction

### Adaptation culturelle

```python
# Original : expression idiomatique
original_fr = "Il pleut des cordes"

# MAUVAIS : traduction littérale
bad_en = "It rains ropes"

# BON : adaptation culturelle
good_en = "It's raining cats and dogs"
```

### Longueur adaptée

```python
# Original anglais (court)
original_en = "Ready."
# = 6 caractères, 0.4 s

# Traduction française (plus long)
trad_fr = "C'est prêt."
# = 11 caractères, 0.7 s

# Traduction allemand (encore plus long)
trad_de = "Es ist fertig."
# = 14 caractères, 0.9 s
```

### Contrainte de durée

```python
def translate_with_duration(original, target_lang, max_duration):
    """Traduire en respectant la durée maximale."""
    translation = translate(original, target_lang)
    
    # Si trop long, raccourcir
    while len(translation) / 15 > max_duration:  # 15 cps
        translation = shorten(translation)
    
    return translation
```

## LanguagePackage

```python
language_package = {
    "languages": ["fr", "en", "es"],
    "dialogues": {
        "fr": [
            {"speaker": "barista", "text": "Le café est prêt.", "start": 0.5, "end": 2.5},
            {"speaker": "client", "text": "Merci.", "start": 3.0, "end": 4.0}
        ],
        "en": [
            {"speaker": "barista", "text": "The coffee is ready.", "start": 0.5, "end": 2.3},
            {"speaker": "client", "text": "Thanks.", "start": 3.0, "end": 3.8}
        ],
        "es": [
            {"speaker": "barista", "text": "El café está listo.", "start": 0.5, "end": 2.6},
            {"speaker": "client", "text": "Gracias.", "start": 3.0, "end": 4.1}
        ]
    },
    "subtitles": {
        "fr": "subtitles/fr/subtitles_v1.srt",
        "en": "subtitles/en/subtitles_v1.srt",
        "es": "subtitles/es/subtitles_v1.srt"
    },
    "voices": {
        "fr": "voices/fr/",
        "en": "voices/en/",
        "es": "voices/es/"
    }
}
```

## Validation

```python
def validate_translation(original, translation, target_lang):
    """Valider une traduction."""
    issues = []
    
    # Vérifier la longueur
    max_chars = 42
    if len(translation) > max_chars * 2:  # 2 lignes max
        issues.append("Trop de caractères")
    
    # Vérifier le glossaire
    for term in glossary["fr"]:
        if term in original and glossary[target_lang][term] not in translation:
            issues.append(f"Terme '{term}' mal traduit")
    
    # Vérifier la durée
    duration = len(translation) / 15  # 15 cps
    original_duration = len(original) / 15
    if duration > original_duration * 1.5:
        issues.append("Traduction trop longue")
    
    return issues
```

## Erreurs courantes

1. **Traduction littérale** : le sens est perdu.
2. **Incohérence** : un terme traduit différemment dans la même scène.
3. **Trop long** : le sous-titre dépasse la durée du plan.
4. **Oublier le contexte** : la traduction ne correspond pas à la scène.
5. **Mauvais glossaire** : noms propres traduits, termes techniques mal rendus.
6. **Pas de relecture** : la traduction n'est pas vérifiée en contexte.

## Règles

- Traduire l'intention, pas mot à mot ; respecter le ton et le registre.
- Contraintes de longueur : sous-titres (débit lisible) et durées de plans.
- Traduire aussi l'interface et les métadonnées (cas d'usage ADD : langues de l'interface).
- Garder un glossaire cohérent (noms propres, termes techniques) par langue.
- Livrer un `LanguagePackage` : dialogues, sous-titres, voix, métadonnées, interface.
- Revoir en contexte (contexte de scène) avant publication.
