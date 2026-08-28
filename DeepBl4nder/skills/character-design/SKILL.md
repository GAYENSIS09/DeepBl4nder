---
name: character-design
description: Conception de personnages 3D : proportions, styles, pipelines de production.
---

# Character Design

Concevoir des personnages 3D crédibles et expressifs pour l'animation.

## Styles visuels

| Style         | Proportions           | Géométrie         | Usage                    |
|---------------|----------------------|-------------------|--------------------------|
| Réaliste      | 7.5 têtes (humble)   | Détaillée         | Films, publicités        |
| Cartoon       | 4-6 têtes           | Semi-détaillée    | Animation, séries        |
| Anime/Manga   | 6-7 têtes           | Mixte             | Storytelling, web        |
| Low-poly      | Varié                | Simplifiée        | Jeux, prototypage        |
| Stylisé       | Exagéré              | Primitive+        | Contenu social, rapide   |

## Pipelines de production

### Pipeline Marvel/DC (personnages réalistes)
1. Sculpture numérique (ZBrush/Blender)
2. Retopology (mesh léger)
3. UV unwrapping
4. Texturing (Substance/PBR)
5. Rigging (armature complète)
6. Blendshapes (expressions faciales)
7. Animation (keyframes + mocap)

### Pipeline Disney/Pixar (personnages stylisés)
1. Modélisation directe (Blender)
2. Subdivision surface
3. Matériaux procéduraux
4. Rigging simplifié
5. Shape keys (expressions)
6. Animation procédurale

### Pipeline Anime (personnages 2D/3D)
1. Modélisation cel-shading
2. Matériaux non-réalistes
3. Rigging pour speaking
4. Lip sync phonème→blendshape
5. Animation par steps (pose-to-pose)

## Proportions de base

### Personnage réaliste (adulte)
```python
# Hauteur totale = 7.5 têtes
head_height = total_height / 7.5
shoulder_width = head_height * 2.5
hip_width = head_height * 1.8
arm_length = total_height * 0.4
leg_length = total_height * 0.45

# Positionnement
eye_level = total_height * 0.93  # Les yeux sont à 93% de la hauteur
center_of_mass = total_height * 0.55  # Centre de gravité
```

### Enfant (4-6 ans)
```python
# Hauteur totale = 4-5 têtes
head_height = total_height / 4.5
shoulder_width = head_height * 2.0
# Tête plus grande, jambes plus courtes
```

### Super-héros
```python
# Hauteur totale = 8-8.5 têtes
head_height = total_height / 8.5
shoulder_width = head_height * 3.0  # Épaules larges
torso_width = head_height * 2.5
```

## Géométrie procédurale

### Primitives de base
```python
import bpy

# Tête
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(0, 0, 1.6))

# Torse
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.0))
# Scale pour le torse
bpy.context.object.scale = (0.3, 0.2, 0.4)

# Bras
bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.6, location=(0.35, 0, 1.2))
# Rotation pour incliner le bras
bpy.context.object.rotation_euler = (0, 0, 0.3)

# Jambes
bpy.ops.mesh.primitive_cylinder_add(radius=0.07, depth=0.7, location=(0.1, 0, 0.35))
```

### Modifiers courants
```python
# Subdivision pour lisser
subsurf = obj.modifiers.new("Subsurf", 'SUBSURF')
subsurf.levels = 2
subsurf.render_levels = 3

# Mirror pour symétrie
mirror = obj.modifiers.new("Mirror", 'MIRROR')
mirror.use_mirror_merge = True

# Solidify pour l'épaisseur
solidify = obj.modifiers.new("Solidify", 'SOLIDIFY')
solidify.thickness = 0.02
```

## Matériaux pour personnages

### Peau réaliste
```python
mat = bpy.data.materials.new(name="Skin")
mat.use_nodes = True
nodes = mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")

# Subsurface scattering pour la peau
bsdf.inputs["Subsurface Weight"].default_value = 0.3
bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
bsdf.inputs["Base Color"].default_value = (0.8, 0.6, 0.5, 1)
bsdf.inputs["Roughness"].default_value = 0.4
```

### Matériaux cartoon
```python
mat = bpy.data.materials.new(name="Cartoon")
mat.use_nodes = True
nodes = mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")

bsdf.inputs["Base Color"].default_value = (0.8, 0.2, 0.2, 1)
bsdf.inputs["Roughness"].default_value = 0.8
bsdf.inputs["Specular IOR Level"].default_value = 0.0  # Pas de reflets
```

## Expressions faciales (Blendshapes)

### Shape keys de base
```python
# Créer les shape keys
shape_keys = obj.data.shape_keys

# Fondre le mesh dans la shape key de base
for key_name in ["mouth_open", "mouth_smile", "mouth_frown",
                  "eyebrow_up", "eyebrow_down",
                  "eye_blink", "eye_wide"]:
    obj.shape_key_add(name=key_name, from_mix=False)

# Animer les shape keys
key = obj.data.shape_keys.key_blocks["mouth_smile"]
key.value = 1.0  # Bouche souriante
key.keyframe_insert(data_path="value", frame=10)
```

## Règles

- Commencer par des primitives, affiner progressivement
- Toujours garder la symétrie (Mirror modifier)
- Utiliser des materials PBR pour le réalisme
- Planifier les blendshapes AVANT le rigging
- Tester les proportions avec un squelette basique
- Exporter en FBX/glTF pour le partage
