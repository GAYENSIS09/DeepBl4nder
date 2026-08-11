---
name: camera
description: Définir cadrage, focale et mouvement de caméra au service de l'intention.
---

# Caméra

Décider où mettre la caméra et comment elle bouge. Chaque choix de caméra est un choix narratif.

## Focal et perspective

La focale détermine la **relation émotionnelle** entre le spectateur et le sujet.

| Focal | Effet | Usage |
|-------|-------|-------|
| **14-24mm** | Ultra-grand angle, déformation, impressionniste | Effets spéciaux, architecture, vertige |
| **24-35mm** | Grand angle, contexte, dynamique | Scènes d'action, paysages, établissement |
| **50mm** | Proche de l'œil humain, naturel | Scènes de dialogue, plan moyen |
| **85mm** | Isolement modéré, bokeh léger | Portraits, interviews |
| **135-200mm** | Forte compression, isolation | Portraits serrés, espionnage, voyeurisme |

```python
import bpy

cam = bpy.data.cameras.new(name="Camera")
cam.lens = 50  # mm — focale
cam.sensor_width = 36  # mm — capteur full-frame
cam.dof.use_dof = True  # profondeur de champ
cam.dof.focus_distance = 5.0  # mètres
cam.dof.aperture_fstop = 2.8  # ouverture (plus petit = plus de flou)

cam_obj = bpy.data.objects.new("Camera", cam)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj
```

### Focal et distance de focalisation

- `lens` = focale en mm. `sensor_width` dépend du capteur (36mm = full-frame, 22mm = APS-C).
- **Depth of Field** : `aperture_fstop` contrôle le flou. f/1.4 = très peu de DOF, f/16 = tout net.
- **Focus distance** : distance du point focal en mètres. Calculer avec `dobj = (cam.location - target.location).length`.

## Cadrages standards

### Plan large (Wide / Establishing)
- Focal : 24-35mm
- Hauteur : hauteur d'œil ou légèrement basse
- Montre l'environnement, établit le lieu

### Plan moyen (Medium)
- Focal : 50-85mm
- Hauteur : hauteur d'œil
- Coupe au niveau de la taille ou des genoux
- Le plus naturel, le plus utilisé

### Plan rapproché (Close-up)
- Focal : 85-135mm
- Hauteur : hauteur d'œil
- Montre le visage, les émotions
- Forte DOF pour isoler

### Plan très rapproché (Extreme Close-up)
- Focal : 100-200mm
- Détails : yeux, mains, objet
- DOF très faible

## Angles de caméra

```python
import math

# Niveau d'œil (neutre)
cam_obj.location = (0, -5, 1.7)  # hauteur des yeux
cam_obj.rotation_euler = (math.radians(90), 0, 0)

# Contre-plongée (le sujet paraît puissant)
cam_obj.location = (0, -3, 0.5)
cam_obj.rotation_euler = (math.radians(75), 0, 0)

# Plongée (le sujet paraît faible, vulnérable)
cam_obj.location = (0, -3, 8)
cam_obj.rotation_euler = (math.radians(105), 0, 0)

# Dutch angle (déséquilibre, tension)
cam_obj.rotation_euler = (math.radians(90), 0, math.radians(15))
```

- **Niveau d'œil** : neutre, équivalent au spectateur.
- **Contre-plongée** : caméra basse, regarde vers le haut → le sujet paraît grand, menaçant, héroïque.
- **Plongée** : caméra haute, regarde vers le bas → le sujet paraît petit, vulnérable, soumis.
- **Dutch angle** : inclinaison latérale → déséquilibre, folie, tension.

## Mouvements de caméra

### Fixe (tripod)
```python
# Pas de clé d'animation = plan fixe
# Le mouvement vient uniquement des objets dans le cadre
```

### Travelling (dolly)
```python
import math

# Début
cam_obj.location = (-5, -5, 1.7)
cam_obj.keyframe_insert(data_path="location", frame=1)

# Fin
cam_obj.location = (5, -5, 1.7)
cam_obj.keyframe_insert(data_path="location", frame=250)

# Interpolation linéaire (constante)
for fcurve in cam_obj.animation_data.action.fcurves:
    for kf in fcurve.keyframe_points:
        kf.interpolation = 'LINEAR'
```

### Pan (rotation)
```python
# Début
cam_obj.rotation_euler = (math.radians(90), 0, math.radians(-30))
cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)

# Fin
cam_obj.rotation_euler = (math.radians(90), 0, math.radians(30))
cam_obj.keyframe_insert(data_path="rotation_euler", frame=250)
```

### Tilt (inclinaison verticale)
```python
cam_obj.rotation_euler = (math.radians(80), 0, 0)  # regarder vers le haut
cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)
```

### Handheld (main levée)
```python
import random
import math

# Ajouter du bruit aléatoire sur chaque frame
for frame in range(1, 251):
    cam_obj.location.x += random.uniform(-0.01, 0.01)
    cam_obj.location.y += random.uniform(-0.01, 0.01)
    cam_obj.location.z += random.uniform(-0.005, 0.005)
    cam_obj.keyframe_insert(data_path="location", frame=frame)
```

## Règles de mouvement

- **Motivé** : chaque mouvement a une raison (suivre un personnage, révéler un élément).
- **Pas de mouvement gratuit** : un plan fixe est préférable à un mouvement injustifié.
- **Vitesse constante** : sauf intention dramatique, pas d'accélération/décélération brutale.
- **Ease in/out** : pour les mouvements expressifs, utiliser `BEZIER` interpolation avec handles ajustés.
- **Coordonner avec la lumière** : le mouvement de caméra ne doit pas créer de flashs ou d'ombres cassantes.

## Erreurs courantes

1. **Focal trop courte** : déformation des visages en close-up (ne pas utiliser < 50mm pour les portraits).
2. **Pas de DOF** : tout est net, pas d'isolation du sujet.
3. **Mouvement non motivé** : travelling inutile qui distraction le spectateur.
4. **Oublier la hauteur** : caméra toujours à 1.5m = cadrage monotone.
5. **Interpolation Bezier par défaut** : mouvements qui "dérivent" au lieu de being constants.
6. **Dutch angle abusé** : inclinaison constante = perte d'impact.

## Règles

- Choisir la focale selon le rapport au personnage (focale ≠ zoom : perspective).
- Position et hauteur : œil, contre-plongée, plongée — chaque choix a un sens narratif.
- Mouvement motivé : travelling, pan, handheld ; pas de mouvement gratuit.
- DOF : utiliser `aperture_fstop` pour isoler le sujet (f/1.4-2.8) ou montrer le contexte (f/8-16).
- Coordonner avec la lumière : soleil/lampe côté caméra ou contre, avec intention.
- Sortir une `CameraSpec` (position, rotation, focale, DOF) et un `CameraPass` d'animation.
- Vérifier le cadre sur un render d'essai avant d'engager l'étape d'animation.
