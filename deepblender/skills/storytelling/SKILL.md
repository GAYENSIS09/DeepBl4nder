---
name: storytelling
description: Structurer un récit dramatique : intention, conflit, arc narratif, rythme et thème.
---

# Storytelling

Transformer un brief en structure narrative solide. Le storytelling est la fondation : sans bonne structure, aucun outil technique ne sauvera la vidéo.

## Principes fondamentaux

- **Intention** : une seule phrase qui dit ce que le spectateur doit ressentir.
- **Conflit** : ce qui empêche le personnage d'obtenir ce qu'il veut. Pas de conflit = pas de drame.
- **Économie** : chaque scène doit servir l'intention. Tout le reste est coupé.

## Structure en trois actes (base)

### Acte 1 — Installation (25% de la durée)
- **Objet du désir** : ce que le personnage veut (visible ou caché).
- **Obstacle** : ce qui s'oppose à lui.
- **Déclic** : l'événement qui déclenche l'action.
- Durée typique : 2-3 s pour un plan de 10 s, 25-30% d'un film de 2-3 min.

### Acte 2 — Confrontation (50% de la durée)
- **Escalade** : les obstacles s'accumulent, la tension monte.
- **Point de non-retour** : le personnage ne peut plus revenir en arrière.
- **Crise** : le moment le plus sombre, tout semble perdu.
- Durée typique : 5-6 s pour un plan de 10 s, 50% d'un film.

### Acte 3 — Résolution (25% de la durée)
- **Climax** : la confrontation finale.
- **Résolution** : le nouvel état du monde.
- **Écho** : ce qui reste, la leçon, le silence.
- Durée typique : 2-3 s pour un plan de 10 s, 25% d'un film.

## Rythme et pacing

| Élément | Rôle | Exemple |
|---------|------|---------|
| **Exposition** | Donner l'information | Carte titre, voix off, décor |
| **Action** | Avancer l'histoire | Déplacement, geste, dialogue |
| **Silence** | Créer la tension | Pause, regard, souffle |
| **Enjeu** | Rappeler ce qui est en jeu | Menace, détail, réaction |

- **Rythme** : alterner exposition → action → silence → enjeu.
- **Montée** : la tension doit croître progressivement vers le climax.
- **Respiration** : après un moment fort, laisser un moment calme.

## Personnages

### Arc narratif
```
Désir → Obstacle → Décision → Transformation
```

- **Désir** : ce que le personnage veut (conscient ou inconscient).
- **Obstacle** : ce qui l'en empêche.
- **Décision** : le moment où il choisit (action ou renoncement).
- **Transformation** : comment il change (ou refuse de changer).

### Voix distincte
- **Vocabulaire** : chaque personnage a son lexique.
- **Syntaxe** : phrases courtes (action) vs longues (réflexion).
- **Silence** : ce que le personnage ne dit pas est aussi important.

## Thème

Le thème est la question que la vidéo pose au spectateur.

- Exemples : "Le pouvoir corrompt-il ?", "L'amour survit-il à la distance ?", "La technologie nous rapproche-t-elle ?"
- Le thème doit être **visible** dans chaque scène, pas dit explicitement.
- **Logline** : une phrase qui résume l'histoire + le thème.

## Application au pipeline DeepBl4nder

### Brief → StorySpec
```
Brief: "Vidéo promotionnelle pour un café artisanal"
→ Logline: "Un barista transforme un simple grain en une expérience sensorielle unique"
→ Thème: "L'artisanat comme acte d'amour"
→ Tonalité: chaleureux, intimiste, lent
→ Arc: routine → découverte → création → partage
```

### SceneNarrative par scène
```python
{
    "scene_id": "scene_01",
    "objective": "Établir le monde du barista (routine, ennui)",
    "events": ["Le barista prépare un café machinalement", "Un client entre, indifférent"],
    "stake": "Rien ne change si rien ne change",
    "emotion": "mélancolie, habitude"
}
```

## Erreurs courantes

1. **Pas de conflit** : les événements se succèdent sans tension.
2. **Trop d'information** : le spectateur est noyé sous les détails.
3. **Résolution trop facile** : l'obstacle n'était pas un vrai obstacle.
4. **Scènes qui ne servent pas l'intention** : "beaux moments" sans narration.
5. **Exposition explicite** : dire au lieu de montrer.

## Règles

- Identifier l'intention centrale du brief (une phrase).
- Définir le conflit : ce qui oppose le personnage à son obstacle.
- Construire un arc en trois temps : installation, tension, résolution.
- Rythmer : alterner exposition, action, silence, enjeu.
- Toute scène sert l'intention : couper ce qui ne la sert pas.
- Produire une sortie structurée (`StorySpec`, `SceneNarrative`, `CharacterArc`).
- Le thème doit être visible, pas dit.
