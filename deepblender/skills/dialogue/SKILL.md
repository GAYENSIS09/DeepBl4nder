---
name: dialogue
description: Écrire des dialogues crédibles, caractérisés et adaptés au style et au format.
---

# Dialogue

Écrire des répliques qui font avancer la scène et révèlent les personnages. Le dialogue n'est pas de la conversation réelle — c'est de la conversation compressée.

## Principes fondamentaux

- **Chaque réplique a un but** : révéler, confronter, retarder ou décider.
- **Moins c'est plus** : les meilleures répliques sont courtes.
- **Sous-texte** : ce que le personnage dit n'est pas ce qu'il pense/vécut.

## Timing et durée

### Budget temps par type de réplique

| Type | Durée | Caractères max |
|------|-------|----------------|
| Réplique courte | 1-2 s | 20-30 |
| Réplique moyenne | 2-4 s | 50-80 |
| Réplique longue | 4-6 s | 100-150 |
| Monologue | 6-10 s | 150-250 |

- **Rythme de lecture** : 15-20 caractères/seconde pour les sous-titres.
- **Pause** : prévoir 0.5-1 s de silence après une réplique importante.
- **Chevauchement** : les personnages peuvent se couper la parole (crédible).

### Calcul du budget texte
```python
duration_seconds = 10
chars_per_second = 15  # rythme de lecture confortable
max_chars = duration_seconds * chars_per_second  # 150 caractères

# Répartir entre les personnages
personnages = ["A", "B"]
budget_par_personnage = max_chars // len(personnages)  # 75 chacun
```

## Voix distinctes

### Caractérisation par le langage
- **A** : phrases courtes, vocabulaire technique, pas de superlatifs.
- **B** : phrases longues, métaphores, émotionnel.
- **C** : questions, hésitations, sous-texte.

### Exemple
```
A: "Le café est prêt."
B: "Il y a quelque chose dans cette tasse... quelque chose qu'on ne trouve pas ailleurs."
A: "C'est du Sumatra. Torréfaction locale."
B: "C'est comme si tu avais mis un peu de... je ne sais pas... d'âme dedans."
```

## Sous-texte

Le sous-texte est ce que le personnage **veut dire** mais ne dit pas.

| Dit | Pense | Sous-texte |
|-----|-------|------------|
| "Ça va" | "Je suis dévasté" | Déni, protection |
| "C'est bien" | "C'est insuffisant" | Politesse, attente |
| "Je suis occupé" | "Je t'évite" | Conflit, fuite |
| "On verra" | "Non" | Refus indirect |

## Structure d'une réplique

```python
dialogue_spec = {
    "speaker": "barista",
    "text": "Le Sumatra. Torréfaction locale.",
    "duration": 2.5,
    "emotion": "fierté discrète",
    "intention": "révéler son savoir-faire",
    "subtext": "Je prends soin de chaque détail",
    "action": "regarde le café dans la tasse"
}
```

## Patterns de dialogue

### Exposition naturelle
```
# MAUVAIS : exposition directe
"Comme tu le sais, ce café vient de Sumatra et a été torréfié hier."

# BON : exposition integrée dans l'action
"Sumatra. Torréfaction d'hier."
# Le spectateur comprend : c'est un café spécial, préparé avec soin
```

### Confrontation
```
# Le conflit monte
"Tu as goûté le mien ?"
"... Oui."
"Et ?"
" C'est différent."
"Different comment ?"
" Je préfère ne pas répondre."
```

### Silence
```
# Le silence est une réplique
"Tu reviens demain ?"
(3 secondes de silence)
"Je ne sais pas."
```

## Dialogue et sous-titres

- **Contrainte de longueur** : les sous-titres ont une limite de caractères (42/seconde max).
- **Synchronisation** : le texte doit correspondre aux lèvres (ou à l'intention si pas de lip-sync).
- **Traduction** : prévoir la version traduite dès l'écriture (phrases courtes = plus faciles à traduire).

## Erreurs courantes

1. **Exposition explicite** : "Comme tu le sais..." → montrer, pas dire.
2. **Toutes les répliques de même longueur** : pas de rythme.
3. **Pas de sous-texte** : les personnages disent exactement ce qu'ils pensent = plat.
4. **Dialogue d'info** : répliques qui n'existent que pour transmettre de l'information.
5. **Oublier l'action** : le dialogue se passe sans mouvement, sans geste.
6. **Même voix pour tous** : tous les personnages s'expriment de la même façon.

## Règles

- Chaque réplique sert l'intention : révéler, confronter, retarder ou décider.
- Voix distinctes : vocabulaire, syntaxe et silences différents par personnage.
- Sous-texte : ce que le personnage dit n'est pas ce qu'il veut dire.
- Éviter les répliques d'exposition assommantes ; montrer plutôt que raconter.
- Respecter la durée de la séquence (en secondes) pour le volume de texte.
- Livrer un `DialogueSpec` typé par locuteur, avec timestamps relatifs au plan.
- Prévoir la traduction dès l'écriture (phrases courtes = traduisibles).
