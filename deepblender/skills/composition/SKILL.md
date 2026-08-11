---
name: composition
description: Composer les cadres : règle des tiers, lignes, équilibre, profondeur et contraste.
---

# Composition

Décider ce que le cadre montre et comment l'œil le traverse. La composition est l'art de guider le regard du spectateur.

## Principes fondamentaux

1. **Un sujet principal** : le regard doit aller quelque part en premier.
2. **Hiérarchie visuelle** : sujet > contexte > détails.
3. **Économie** : tout élément non nécessaire est retiré.

## Règle des tiers

Diviser le cadre en 9 zones égales (2 lignes horizontales, 2 verticales). Placer les sujets sur les intersections.

```
+-------+-------+-------+
|       |       |       |
|   ●---+-------+       |  ← Sujet sur intersection haute-gauche
|       |       |       |
+-------+-------+-------+
|       |       |       |
|       |       |   ●   |  ← Second sujet sur intersection basse-droite
|       |       |       |
+-------+-------+-------+
```

```python
import bpy

# Placer la caméra pour respecter la règle des tiers
cam = bpy.data.cameras.new("Camera")
cam.lens = 50

cam_obj = bpy.data.objects.new("Camera", cam)
bpy.context.scene.collection.objects.link(cam_obj)

# Sujet à (2, 0, 1) — placé sur le tiers gauche
# Caméra à (0, -5, 1.7) — centre, le sujet est décalé
cam_obj.location = (0, -5, 1.7)
bpy.context.scene.camera = cam_obj
```

## Lignes directrices

### Lignes de force
- **Horizontales** : stabilité, calme (horizon, plans d'eau).
- **Verticales** : puissance, stature (bâtiments, personnages debout).
- **Diagonales** : dynamisme, tension (escaliers, routes en pente).
- **Courbes** : douceur, nature (rivières, visages).

### Convergence
Les lignes directrices convergent vers le sujet. Utiliser les bords du cadre comme "flèches" vers le point d'intérêt.

## Profondeur

### Plans successifs
```
Avant-plan (flou) → Sujet (net) → Arrière-plan (flou)
```

- **Avant-plan** : éléments flous qui créent de la profondeur (feuilles, objets proches).
- **Sujet** : net, isolé.
- **Arrière-plan** : contexte, légèrement flou.

### Profondeur de champ
```python
cam.dof.use_dof = True
cam.dof.focus_distance = 5.0  # distance au sujet
cam.dof.aperture_fstop = 2.8  # plus petit = plus de flou
```

### Perspective
- **Focale courte** (24-35mm) : accentue la profondeur, les objets proches paraissent grands.
- **Focale longue** (85-200mm) : compresse la profondeur, les objets paraissent proches.

## Équilibre visuel

### Poids visuel
- Un personnage à gauche = un élément à droite pour équilibrer.
- La "lourdeur" visuelle : couleurs foncées > claires, textures > lisses, visages > objets.

### Asymétrie
- L'équilibre symétrique est statique, parfois ennuyeux.
- L'asymétrie crée de la dynamique mais doit rester équilibrée.

## Espace de regard

```python
# Personnage qui regarde à droite → laisser de l'espace à droite
cam_obj.location = (-2, -5, 1.7)  # caméra à gauche
# Le personnage est cadré à gauche, regarde vers la droite
```

- **Headroom** : espace au-dessus de la tête. Pas trop (gaspillage) pas trop peu (oppressant).
- **Lead room** : espace devant le personnage. Si il marche à droite, laisser de l'espace à droite.

## Contraste et lumière

- Le regard va d'abord vers les zones les plus lumineuses.
- Utiliser la lumière pour guider le regard, pas seulement pour éclairer.
- **Contraste de couleur** : un élément coloré dans un décor neutre attire l'œil.
- **Contraste de texture** : un élément lisse dans un décor texturé attire l'œil.

## Erreurs courantes

1. **Sujet au centre** : composition statique, pas de dynamisme.
2. **Trop d'éléments** : le regard ne sait pas où aller.
3. **Pas de profondeur** : image "plate", pas de recul.
4. **Tête coupée** : ne pas couper au niveau des articulations (genoux, poignets).
5. **Oublier l'arrière-plan** : un bel arrière-plan distrayant le sujet.
6. **Horizon au centre** : souvent mieux de le placer sur un tiers.

## Règles

- Règle des tiers pour les sujets et lignes d'horizon.
- Guider le regard : lignes directrices, contraste, profondeur de champ.
- Équilibre et poids visuel ; laisser de l'espace de regard (headroom, lead room).
- Simplicité : retirer du cadre tout ce qui n'apporte rien.
- Traduire en valeurs concrètes : position caméra, focale, hauteur, angle.
- Sortir une `CameraSpec`/`ShotPlan` cohérente avec l'intention émotionnelle.
