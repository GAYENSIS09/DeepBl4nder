---
name: lighting
description: Éclairage de scène Blender (key/fill/rim, intensités, ambiances).
---

# Éclairage

Configurer l'éclairage d'un plan pour servir le brief. La lumière est l'outil émotionnel principal en 3D.

## Principes fondamentaux

- La lumière **crée l'ambiance**, révèle les formes, guide le regard.
- Pas de setup universel : chaque plan a ses propres besoins lumineux.
- Toujours commencer par un éclairage de base (3 points) puis affiner.

## Éclairage à trois points (base)

```python
import bpy
from math import radians

scene = bpy.context.scene
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.02, 0.02, 0.02, 1)  # ambiance sombre
bg.inputs[1].default_value = 0.5

# KEY LIGHT — lumière principale, côté caméra ou à 45°
key = bpy.data.lights.new(name="Key", type='AREA')
key.energy = 200  # Watts (area light)
key.size = 2.0    # mètres
key.color = (1.0, 0.95, 0.9)  # légèrement chaude
key_obj = bpy.data.objects.new("Key", key)
scene.collection.objects.link(key_obj)
key_obj.location = (4, -3, 5)
key_obj.rotation_euler = (radians(45), 0, radians(30))

# FILL LIGHT — lumière d'appoint, côté opposé, moins intense
fill = bpy.data.lights.new(name="Fill", type='AREA')
fill.energy = 50   # 25-50% de la key
fill.size = 4.0    # plus grande = plus douce
fill.color = (0.9, 0.95, 1.0)  # légèrement froide
fill_obj = bpy.data.objects.new("Fill", fill)
scene.collection.objects.link(fill_obj)
fill_obj.location = (-3, -2, 4)
fill_obj.rotation_euler = (radians(30), 0, radians(-30))

# RIM LIGHT — lumière de dos, détache du fond
rim = bpy.data.lights.new(name="Rim", type='AREA')
rim.energy = 150
rim.size = 1.5
rim.color = (1.0, 1.0, 1.0)  # neutre
rim_obj = bpy.data.objects.new("Rim", rim)
scene.collection.objects.link(rim_obj)
rim_obj.location = (0, 4, 5)
rim_obj.rotation_euler = (radians(-30), 0, radians(180))
```

## Types de sources lumineuses

| Type | Usage | bpy type |
|------|-------|----------|
| **Point** | Ampoule omnidirectionnelle | `'POINT'` |
| **Sun** | Lumière directionnelle (soleil) | `'SUN'` |
| **Spot** | projecteur directionnel, portée limitée | `'SPOT'` |
| **Area** | Lumière douce, réaliste | `'AREA'` |
| **Hemi** | Ciel semi-directionnel (ancien) | `'HEMI'` |

- **Area** : la plus réaliste pour les scènes intérieures. `key.size` contrôle la douceur des ombres.
- **Sun** : pour les extérieurs. `sun.energy` est en fait la "force" (pas des watts). Direction = rotation de l'objet.
- **Spot** : pour des effets ciblés (projecteur, phare, lampe de travail). Utiliser `spot_size` et `spot_blend`.

## Ambiances et mood

### Sombre / Dramatique
```python
# Key faible, pas de fill, rim fort
key.energy = 100
fill.energy = 0  # pas de fill = ombres profondes
rim.energy = 200
bg.inputs[0].default_value = (0.005, 0.005, 0.01, 1)
```

### Chaud / Intimiste
```python
key.color = (1.0, 0.85, 0.6)  # orange chaud
key.energy = 150
fill.color = (0.8, 0.7, 0.5)  # warm fill
bg.inputs[0].default_value = (0.03, 0.02, 0.01, 1)
```

### Froid / Scientifique
```python
key.color = (0.8, 0.9, 1.0)  # bleu froid
fill.color = (0.7, 0.8, 0.9)
bg.inputs[0].default_value = (0.01, 0.01, 0.03, 1)
```

### Neutre / Professionnel
```python
key.color = (1.0, 1.0, 1.0)
key.energy = 200
fill.energy = 100  # 50% de la key
bg.inputs[0].default_value = (0.05, 0.05, 0.05, 1)
```

## HDRI (éclairage d'environnement)

```python
import bpy

scene = bpy.context.scene
scene.world.use_nodes = True
tree = scene.world.node_tree
nodes = tree.nodes
links = tree.links

# Nettoyer
for node in nodes:
    nodes.remove(node)

# Créer le setup HDRI
output = nodes.new('ShaderNodeOutputWorld')
env = nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load("//hdri/studio.exr")  # ou .hdr
mapping = nodes.new('ShaderNodeMapping')
coord = nodes.new('ShaderNodeTexCoord')

links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
links.new(mapping.outputs['Vector'], env.inputs['Vector'])
links.new(env.outputs['Color'], output.inputs['Surface'])
```

- HDRI pour les réflexions et l'ambiance globale
- Combiner avec des lights directes pour le contrôle
- Intensité via le node Mapping > Scale ou un Math node Multiply

## Ombres

```python
# Ombres douces (area lights grandes)
key.shadow_soft_size = 3.0  # plus grand = ombres plus douces

# Ombres dures (area lights petites ou sun)
key.shadow_soft_size = 0.1

# Pas d'ombre (pour des lights décoratives)
key.shadow_method = 'NONE'

# Contact shadows (Eevee)
scene.eevee.use_shadow_high_bitdepth = True
scene.eevee.use_soft_shadows = True
```

- **Rayon de l'ombre** : `shadow_soft_size` en mètres. Plus grand = plus doux.
- **Distance** : `shadow CascadeType` en Cycles pour optimiser les ombres lointaines.
- **Contact shadows** (Eevee) : `use_contact_shadow` sur chaque light pour les détails fins.

## Erreurs courantes

1. **Toutes les lights à la même intensité** : pas de hiérarchie = éclairage plat.
2. **Pas de fill** : ombres trop dures, contraste excessif.
3. **Lights surévaluées** : scènes surexposées, perte de détail.
4. **Oublier le world** : fond noir = lumière d'ambiance nulle, scènes sombres inattendues.
5. **Mix color temp** : key chaude + fill chaude = trop monochrome. Alterner warm/cool pour la profondeur.
6. **Shadow method = 'NONE'** sur toutes les lights : pas d'ombre = pas de profondeur.

## Règles

- Construire un éclairage à trois points par défaut (key, fill, rim).
- Adapter l'ambiance au mood du brief (sombre, neutre, chaud, froid).
- Hiérarchiser : key > rim > fill en intensité.
- Choisir le type de light selon l'usage (Area pour intérieur, Sun pour extérieur).
- Varier la température de couleur entre key (neutre/chaude) et fill (froide) pour la profondeur.
- Ombres : plus grandes = plus douces. Utiliser des area lights de grande taille pour un éclairage doux.
- HDRI pour l'ambiance globale + lights directes pour le contrôle.
- Valider sur un render d'essai (32 samples, 50% résolution) avant d'engager le plan final.
- Produire une `LightingSpec` typée avant le script bpy.
