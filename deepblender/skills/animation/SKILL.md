---
name: animation
description: Animation simple et déterministe (mouvement, rotation, keyframes).
---

# Animation

Animer des objets de façon déterministe dans Blender. Pour les plans courts (5-10 s), l'animation doit être précise et reproductible.

## Principes fondamentaux

- **Moins c'est plus** : animer le strict nécessaire. Un plan de 10 s peut avoir 2-3 animations.
- **Déterminisme** : chaque frame doit produire la même image. Pas de hasard, pas de simulations non cachées.
- **Timing** : la durée de l'animation = durée du plan en frames.

## Calcul des frames

```python
import bpy

scene = bpy.context.scene
fps = scene.render.fps  # 24, 25, ou 30
duration_seconds = 8  # durée du plan

total_frames = fps * duration_seconds  # 24fps × 8s = 192 frames
scene.frame_start = 1
scene.frame_end = total_frames
```

## Keyframes sur position

```python
import math

obj = bpy.data.objects["MonObjet"]

# Frame 1 : position initiale
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)

# Frame 192 : position finale
obj.location = (5, 3, 2)
obj.keyframe_insert(data_path="location", frame=192)

# Interpolation linéaire (constante, pas d'accélération)
for fcurve in obj.animation_data.action.fcurves:
    for kf in fcurve.keyframe_points:
        kf.interpolation = 'LINEAR'
```

## Keyframes sur rotation

```python
import math

obj = bpy.data.objects["MonObjet"]

# Rotation Y de 0 à 360°
obj.rotation_euler = (0, 0, 0)
obj.keyframe_insert(data_path="rotation_euler", frame=1)

obj.rotation_euler = (0, math.radians(360), 0)
obj.keyframe_insert(data_path="rotation_euler", frame=192)

# Ou rotation en Z (le plus courant pour les objets tournants)
obj.rotation_euler = (0, 0, 0)
obj.keyframe_insert(data_path="rotation_euler", frame=1)
obj.rotation_euler = (0, 0, math.radians(360))
obj.keyframe_insert(data_path="rotation_euler", frame=192)
```

## Keyframes sur échelle

```python
obj = bpy.data.objects["MonObjet"]

# Apparition progressive (scale de 0 à 1)
obj.scale = (0, 0, 0)
obj.keyframe_insert(data_path="scale", frame=1)

obj.scale = (1, 1, 1)
obj.keyframe_insert(data_path="scale", frame=24)  # 1 seconde
```

## Interpolations

```python
# Linéaire (constante) — le plus courant
for kf in fcurve.keyframe_points:
    kf.interpolation = 'LINEAR'

# Bezier (accel/décel) — pour les mouvements naturels
for kf in fcurve.keyframe_points:
    kf.interpolation = 'BEZIER'

# Constant (pas à pas) — pour les changements brusques
for kf in fcurve.keyframe_points:
    kf.interpolation = 'CONSTANT'

# Ajuster les handles Bezier (ease in/out)
for kf in fcurve.keyframe_points:
    kf.handle_left_type = 'AUTO'
    kf.handle_right_type = 'AUTO'
```

- **LINEAR** : vitesse constante, idéal pour les mouvements mécaniques.
- **BEZIER** : accélération/décélération, idéal pour les mouvements naturels.
- **CONSTANT** : changement instantané, idéal pour les switchs de visibility.

## Ease In / Ease Out (Beziers)

```python
import math

# Ease In (lent au début, accélère)
for kf in fcurve.keyframe_points:
    kf.interpolation = 'BEZIER'
    kf.handle_left_type = 'ALIGNED'
    kf.handle_right_type = 'ALIGNED'
    # Ralentir le début
    kf.co.x += 0  # pas de changement
    kf.handle_left.y = kf.co.y  # point de contrôle à l'horizontale

# Ease Out (rapide au début, ralentit)
for kf in fcurve.keyframe_points:
    kf.interpolation = 'BEZIER'
    kf.handle_left_type = 'ALIGNED'
    kf.handle_right_type = 'ALIGNED'
    # Accélérer la fin
    kf.handle_right.y = kf.co.y
```

## Patterns courants

### Loop infini
```python
# Ajouter la modifier F-Curve
fcurve = obj.animation_data.action.fcurves[0]  # location X par exemple
modifier = fcurve.modifiers.new(type='CYCLES')
modifier.mode_before = 'REPEAT'  # ou 'REVERSE' pour un ping-pong
modifier.mode_after = 'REPEAT'
```

### Animation dirigée (Track To)
```python
import bpy

# L'objet suit une cible
constraint = obj.constraints.new(type='TRACK_TO')
constraint.target = bpy.data.objects["Cible"]
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'
```

### Animation par drivers
```python
# Rotation basée sur un custom property
obj["rotation_speed"] = 0.5  # tours par seconde

driver = obj.driver_add('rotation_euler', 2)  # Z rotation
driver.driver.type = 'SCRIPTED'
var = driver.driver.variables.new()
var.name = "speed"
var.type = 'SINGLE_PROP'
var.targets[0].id = obj
var.targets[0].data_path = '["rotation_speed"]'
driver.driver.expression = "frame * speed * 0.0174533"  # radians
```

## Animation de caméra

```python
import math

cam = bpy.data.objects["Camera"]

# Travelling avant
cam.location = (0, -10, 1.7)
cam.keyframe_insert(data_path="location", frame=1)

cam.location = (0, -3, 1.7)
cam.keyframe_insert(data_path="location", frame=192)

# Pan de gauche à droite
cam.rotation_euler = (math.radians(90), 0, math.radians(-20))
cam.keyframe_insert(data_path="rotation_euler", frame=1)

cam.rotation_euler = (math.radians(90), 0, math.radians(20))
cam.keyframe_insert(data_path="rotation_euler", frame=192)
```

## Erreurs courantes

1. **Trop de keyframes** : animation "tremblante". Utiliser le minimum de keyframes nécessaires.
2. **Oublier l'interpolation** : Bezier par défaut = mouvement "dérivant". Forcer LINEAR si constant.
3. **Frames hors range** : keyframe à frame 200 alors que `frame_end = 192`. Vérifier les bornes.
4. **Rotation > 360°** : Blender interprète comme rotation partielle. Utiliser des drivers pour les rotations infinies.
5. **Pas de easing** : mouvement robotique. Utiliser Bezier pour les mouvements naturels.
6. **Animation non déterministe** : simulations, particules non cachées. Tout doit être keyframé ou caché.

## Règles

- Utiliser des keyframes explicites sur des frames calculées (`frame_count = fps × duration_seconds`).
- Animer le strict nécessaire pour le plan (5-10 s).
- Interpolation : LINEAR pour mécanique, BEZIER pour naturel, CONSTANT pour switchs.
- Vérifier le range de frames (frame_start à frame_end) avant d'animer.
- Pas de mouvements > 360° sans driver. Utiliser un driver pour les rotations continues.
- Produire une `AnimationSpec` typée avant le script bpy.
- Valider sur un rendu d'essai (2-3 frames) avant de lancer le rendu complet.
