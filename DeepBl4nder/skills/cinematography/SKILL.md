---
name: cinematography
description: Choix de caméra et composition de plans (focales, cadrages, mouvements).
---

# Cinématographie

Décider la caméra d'un plan : focale, position, cadrage, mouvement. Chaque choix technique est un choix esthétique.

## Focal et intention

| Focal | Distance | Effet émotionnel | Usage typique |
|-------|----------|------------------|---------------|
| **14mm** | Très proche | Vertige, déformation | Effets spéciaux, architecture |
| **24mm** | Proche | Dynamique, contexte | Action, paysages |
| **35mm** | Proche-moyen | Naturel, légèrement élargi | Scènes d'établissement |
| **50mm** | Moyen | Neutre, proche de l'œil humain | Dialogue, portraits moyens |
| **85mm** | Lointain | Isolement, intimité | Portraits, interviews |
| **135mm** | Très loin | Compression, voyeurisme | Espionnage, émotion intense |
| **200mm** | Extrême | Isolation totale | Détails, suspense |

### Distance de travail
- La focale détermine la distance physique nécessaire pour cadrer un sujet.
- **50mm à 5m** = plan moyen.
- **135mm à 15m** = plan rapproché (mais la caméra est loin).

## Cadrages

### Par hauteur

| Cadrage | Position | Effet |
|---------|----------|-------|
| **Plongée** | Caméra haute | Sujet faible, vulnérable |
| **Niveau d'œil** | Caméra à hauteur des yeux | Neutre, équivalent du spectateur |
| **Contre-plongée** | Caméra basse | Sujet puissant, menaçant |
| **Dutch angle** | Incliné | Déséquilibre, folie |

### Par taille

| Cadrage | Taille | Fonction |
|---------|--------|----------|
| **Plan large (ELS)** | Corps entier + contexte | Établir le lieu |
| **Plan moyen (MS)** | Taille | Action, dialogue |
| **Plan rapproché (CU)** | Épaules | Émotion, réaction |
| **Plan très rapproché (ECU)** | Visage | Intensité, intimité |
| **Détail** | Objet/membre | Signification, symbole |

## Mouvements de caméra

### Classification

| Mouvement | Type | Effet |
|-----------|------|-------|
| **Fixe** | Statique | Neutralité, observation |
| **Pan** | Rotation horizontale | Suivre un sujet, révéler |
| **Tilt** | Rotation verticale | Hauteur, échelle |
| **Dolly** | Translation avant/arrière | Approche, éloignement |
| **Truck** | Translation latérale | Parallaxe, profondeur |
| **Crane** | Translation verticale | Élévation, perspective |
| **Handheld** | Instable | Immédiateté, urgence |
| **Steadicam** | Suivi fluide | Immergent, contemplatif |

### Vitesse

```python
# Lent (contemplatif) : 1-2 s pour un mouvement court
# Moyen (naturel) : 0.5-1 s
# Rapide (action) : 0.2-0.5 s
# Très rapide (cut) : < 0.2 s
```

## Composition avancée

### Règle des tiers (rappel)
Placer les sujets sur les intersections des lignes de tiers.

### Triangle de composition
Les trois points d'intérêt forment un triangle dans le cadre.

### Profondeur de champ intentionnelle
```python
# Isolement du sujet
cam.dof.aperture_fstop = 1.4  # très peu de DOF
# Contexte
cam.dof.aperture_fstop = 11  # tout net
```

### Cadre dans le cadre
Utiliser des portes, fenêtres, arcs pour "encadrer" le sujet.

## Motivation du mouvement

Chaque mouvement doit avoir une raison :

| Motivation | Mouvement | Exemple |
|------------|-----------|---------|
| Suivre un personnage | Dolly / Truck | Personnage qui marche |
| Révéler un élément | Pan / Tilt | Découverte d'un objet |
| Montrer l'échelle | Crane | Du visage au paysage |
| Créer de l'urgence | Handheld | Scène d'action |
| Créer de l'immersion | Steadicam | Suivi d'un personnage |

## Erreurs courantes

1. **Focal trop courte en portrait** : déformation des visages (< 50mm).
2. **Mouvement non motivé** : travelling qui n'a pas de raison.
3. **Dutch angle permanent** : perte d'impact.
4. **Pas de variation** : tous les plans à la même focale/hauteur.
5. **Oublier l'arrière-plan** : le cadrage coupe l'information importante.
6. **Trop de mouvement** : le spectateur est distrait.

## Règles

- Adapter la focale au propos : longues focales pour isoler, courtes pour le contexte.
- Respecter la règle des tiers pour la composition.
- Préférer des mouvements de caméra motivés (plan fixe si rien ne le justifie).
- Varier les cadrages (hauteur, taille, focale) pour la dynamique.
- Produire une `CameraSpec` typée, jamais du bpy brut.
- Vérifier le cadre sur un render d'essai avant d'engager l'animation.
