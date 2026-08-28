---
name: modeling
description: Créer et modifier la géométrie Blender : primitives, extrusion, boucles, topologie propre.
---

# Modeling

Créer des assets 3D avec une topologie propre, en bpy déterministe. Le modelage est la fondation de tout le pipeline 3D.

## Principes fondamentaux

- **Quads avant tout** : les quadrilatères se déplient, se déforment, se subdivisionnent correctement.
- **Topologie propre** : le flux de polygones suit la forme de l'objet.
- **Économie** : le minimum de polygons nécessaire pour la forme.
- **Déterminisme** : chaque opération produit le même résultat.

## Primitives de base

```python
import bpy

# Cube
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "prop_table"

# Sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=(0, 0, 3))
sphere = bpy.context.active_object
sphere.name = "prop_boule"

# Cylinder
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=2, vertices=32, location=(0, 0, 0))
cyl = bpy.context.active_object
cyl.name = "prop_poteau"

# Plane
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = "env_sol"

# Cone
bpy.ops.mesh.primitive_cone_add(radius1=1, radius2=0, depth=2, vertices=32, location=(0, 0, 3))
cone = bpy.context.active_object
cone.name = "prop_toit"
```

## Opérations de modelage

### Extrusion
```python
import bpy

bpy.ops.mesh.primitive_cube_add(size=2)
obj = bpy.context.active_object

# Passer en mode édition
bpy.ops.object.mode_set(mode='EDIT')

# Sélectionner une face
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.mesh.select_linked_pick(deselect=False, location=(0, 0, 1))

# Extruder
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 2)})

bpy.ops.object.mode_set(mode='OBJECT')
```

### Inset (face insets)
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
# Sélectionner la face du haut
bpy.ops.mesh.select_linked_pick(deselect=False, location=(0, 0, 2))
bpy.ops.mesh.inset_thickness(thickness=0.2, depth=0)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Loop Cut
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.loopcut_slide(
    TRANSFORM_OT_edge_slide={"value": 0.5, "single_side": False},
    MESH_OT_loopcut={"number_cuts": 3, "smoothness": 0}
)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Bevel (arrondi)
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.bevel(offset=0.1, segments=3, profile=0.5)
bpy.ops.object.mode_set(mode='OBJECT')
```

## Topologie

### Flux de polygones
- Les edge loops doivent suivre la forme de l'objet.
- Pour un visage : boucles autour des yeux, de la bouche, du nez.
- Pour un cylindre : boucles verticales + horizontales régulières.

### Éviter
- **N-gons** (faces à > 4 vertices) : causent des artefacts de rendu.
- **Triangles visibles** : déforment les matériaux lisses.
- **Poles à > 5 edges** : créent des distorsions.
- **Vertices non mergeés** : coutures visibles.

### Règle d'or
```
Quads réguliers > Quads irréguliers > Triangles > N-gons
```

## Scale et orientation

```python
# Appliquer la scale (CRITIQUE avant export/render)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Vérifier l'orientation
# Blender utilise Z-up par défaut
# Certains moteurs utilisent Y-up (Unity, Unreal)
```

- **Scale 1.0** = 1 mètre dans Blender.
- **Orientation** : Z-up (Blender) vs Y-up (autres moteurs). Vérifier le pipeline.
- **Origine** : au centre de masse ou au bas de l'objet (selon usage).

## Nommage

```python
# Convention : obj_<type>_<name>
obj.name = "prop_table_oak"
obj.data.name = "mesh_table_oak"

# Collections
col = bpy.data.collections.new("props")
bpy.context.scene.collection.children.link(col)
```

## Patterns courants

### Objet simple (table)
```python
import bpy

# Surface
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1))
top = bpy.context.active_object
top.name = "table_top"
top.scale = (1.5, 0.8, 0.05)
bpy.ops.object.transform_apply(scale=True)

# 4 pieds
for i, pos in enumerate([(0.6, 0.3), (-0.6, 0.3), (0.6, -0.3), (-0.6, -0.3)]):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=1, location=(pos[0], pos[1], 0.5))
    leg = bpy.context.active_object
    leg.name = f"table_leg_{i}"
```

### Objet organique (roche)
```python
import bpy
import random

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1)
rock = bpy.context.active_object
rock.name = "rock"

# Déformer aléatoirement
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.vertices_randomize(offset=0.3)
bpy.ops.object.mode_set(mode='OBJECT')

# Smooth
bpy.ops.object.modifier_add(type='SUBSURF')
rock.modifiers["Subdivision"].levels = 2
```

## Erreurs courantes

1. **Pas d'apply scale** : matériaux étirés, collision incorrecte.
2. **N-gons** : artefacts de rendu, problèmes de subdivision.
3. **Topologie en chaos** : impossible à animer ou à déplier en UV.
4. **Trop de polygons** : lent à rendre, inutile pour la forme.
5. **Origine au mauvais endroit** : rotation/échelle incorrecte.
6. **Pas de nommage** : confusion dans les scènes complexes.

## Règles

- Démarrer de primitives ; opérer par extrude/inset/loop cut pour garder des quads.
- Garder une topologie propre : quads dominants, éviter les n-gons et triangles visibles.
- Centrer et orienter l'objet sur l'origine ; appliquer la scale avant export.
- Nommer objets et collections explicitement (`obj_<type>_<name>`).
- Vérifier la scale (échelle réaliste) et la norme (Y-up / Z-up selon pipeline).
- Sortir un `AssetSpec` + code bpy réutilisable ; jamais de mesh généré par `exec`.
