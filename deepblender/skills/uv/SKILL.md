---
name: uv
description: Déplier les UV pour un texturing propre : seams, densité uniforme, pack sans chevauchement.
---

# UV Mapping

Préparer le dépliage UV avant texturing. Les UV déterminent comment les textures s'appliquent sur la géométrie.

## Principes fondamentaux

- **Pas de chevauchement** : chaque face a sa propre zone dans l'espace UV (sauf instancing).
- **Densité uniforme** : la taille des texels est cohérente sur toute la surface.
- **Seams sur les arêtes invisibles** : les coutures ne doivent pas être visibles.
- **Orientation** : les îles UV doivent être droites quand c'est possible.

## Seams (coutures)

### Où placer les seams
- **Mâchoires** : derrière la tête, dans les cheveux.
- **Aisselles** : sous les bras, peu visible.
- **Dos** : le long de la colonne.
- **Intérieur des cuisses** : peu visible.
- **Arêtes invisibles** : bords d'objets, jonctions avec d'autres objets.

### Comment définir les seams
```python
import bpy

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')

# Sélectionner les arêtes de seam
bpy.ops.mesh.select_linked_pick(deselect=False, location=(0, 0, 0))
bpy.ops.mesh.mark_seam(clear=False)

bpy.ops.object.mode_set(mode='OBJECT')
```

## Densité texel

### Calcul
```python
# Densité = pixels par unité Blender
texel_density = 1024 / 2  # 1024 pixels pour 2 mètres = 512 px/m

# Pour un objet de 2m x 2m avec 2048x2048 pixels
obj_size = 2.0  # mètres
texture_size = 2048  # pixels
density = texture_size / obj_size  # 1024 px/m
```

### Uniformisation
```python
# Blender : UV > Average Island Scale
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode='OBJECT')
```

## Projection

### Projection from view
```python
# Pour les surfaces planes (murs, sols)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')

# Aligner la caméra face à la surface
bpy.ops.view3d.view_axis(type='TOP')

# Project from view
bpy.ops.uv.project_from_view(camera_bounds=False, margin=0.1)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Smart UV Project
```python
# Pour les objets complexes (automatique)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Cubic projection
```python
# Pour les objets cubiques
bpy.ops.uv.cube_project(cube_size=2, margin=0.1)
```

## Packing (empaquetage)

```python
# Pack les îles UV sans chevauchement
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.pack_islands(margin=0.001)  # margin en pixels UV
bpy.ops.object.mode_set(mode='OBJECT')
```

- **Margin** : espace entre les îles. 0.001 = 1 pixel de marge à 1024px.
- **Padding** : extension des îles pour éviter les coutures visibles.

## Orientation des îles

```python
# Aligner les îles UV
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.align(axis='ALIGN_X')  # ou ALIGN_Y
bpy.ops.object.mode_set(mode='OBJECT')
```

## Vérification

```python
# Checker map pour vérifier les UV
checker = bpy.data.images.new("checker", width=1024, height=1024)
# Remplir avec un motif damier (procédural ou image)

mat = bpy.data.materials.new("checker_mat")
mat.use_nodes = True
tree = mat.node_tree
img_tex = tree.nodes.new('ShaderNodeTexImage')
img_tex.image = checker
```

## Patterns courants

### Personnage
```
Corps : projection cylindrique + seams sur les côtés
Tête : projection sphérique + seam derrière
Mains : projection from view + seams sur les doigts
```

### Environnement
```
Sol : projection from view (top)
Murs : projection from view (front)
Plafond : projection from view (bottom)
```

### Prop simple
```
Cube : cubique projection
Cylindre : cylindrique projection + caps séparés
```

## Erreurs courantes

1. **Chevauchement d'îles** : deux faces sur la même zone = texture dupliquée.
2. **Densité inégale** : certaines parties ont des texels grands, d'autres petits.
3. **Seams visibles** : coutures qui passent sur des surfaces visibles.
4. **Îles tournées** : textures qui paraissent "penchées".
5. **Pas de margin** : coutures visibles à cause du manque d'espace.
6. **UV en dehors de 0-1** : textures qui ne s'appliquent pas.

## Règles

- Placer les seams sur les arêtes invisibles (mâchoires, aisselles, dos).
- Uniformiser la densité texel pour éviter les étirements.
- Packer les îles sans chevauchement avec une marge suffisante.
- Respecter l'orientation des îles (projection from view pour les surfaces planes).
- Prévoir du padding (bleed) pour l'antialiasing des bords de texture.
- Sortir un `UVSpec` (map, densité, résolution cible) associé au `TextureSet`.
