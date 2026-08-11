---
name: blender-api-reference
description: Référence complète de l'API Blender Python (bpy) pour la génération de scripts.
---

# Blender Python API Reference

Référence complète de `bpy` pour générer des scripts Blender corrects et robustes.
Source : https://docs.blender.org/api/current/

## Imports autorisés

```python
import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Euler, Quaternion, Color
import random
import json
import os
```

## Modules principaux

| Module | Usage |
|--------|-------|
| `bpy.data` | Accès aux données de la scène (objets, matériaux, caméras...) |
| `bpy.context` | Contexte actuel (objet actif, scène, mode...) |
| `bpy.ops` | Opérateurs (actions Blender : ajouter, supprimer, transformer...) |
| `bpy.types` | Types Blender (classes pour les propriétés) |
| `mathutils` | Types mathématiques (Vector, Matrix, Quaternion) |
| `bmesh` | Édition de mesh avancée (bmesh API) |

---

## bpy.data — Accès aux données

### Collections

```python
# Objets
bpy.data.objects                    # Tous les objets
bpy.data.objects["Cube"]            # Par nom
bpy.data.objects.new("Name", mesh)  # Créer un objet

# Meshes
bpy.data.meshes
bpy.data.meshes.new("Name")

# Matériaux
bpy.data.materials
bpy.data.materials.new("Name")

# Caméras
bpy.data.cameras
bpy.data.cameras.new("Name")

# Lumières
bpy.data.lights
bpy.data.lights.new("Name", type='POINT')

# Images
bpy.data.images
bpy.data.images.load("//path/to/image.png")

# Textures
bpy.data.textures

# Collections (groupes)
bpy.data.collections
bpy.data.collections.new("Name")

# Scènes
bpy.data.scenes

# Curves
bpy.data.curves
bpy.data.curves.new("Name", type='CURVE')

# Fonts
bpy.data.fonts
```

### Méthodes communes des collections

```python
collection = bpy.data.objects
collection.remove(obj)           # Supprimer
collection.active_index = 0      # Index actif
len(collection)                  # Nombre d'éléments
"Name" in collection             # Vérifier existence
collection.get("Name")           # Retourne None si absent
collection.get("Name", default)  # Avec valeur par défaut
```

---

## bpy.context — Contexte actuel

```python
bpy.context.active_object         # Objet actif
bpy.context.selected_objects      # Objets sélectionnés (liste)
bpy.context.selected_objects[0]   # Premier sélectionné
bpy.context.scene                 # Scène active
bpy.context.view_layer            # Calque de vue
bpy.context.tool_settings         # Paramètres d'outils
bpy.context.preferences           # Préférences utilisateur
bpy.context.window                # Fenêtre active
bpy.context.space_data            # Espace de travail (éditeur actif)
bpy.context.collection            # Collection courante
```

### Contexte mode-spécifique

```python
bpy.context.mode                  # 'OBJECT', 'EDIT_MESH', 'SCULPT', etc.
bpy.context.edit_object           # Objet en mode édition
bpy.context.object                # Objet courant (= active_object)
```

---

## bpy.types — Types de propriétés

### Object (bpy.types.Object)

```python
obj = bpy.context.active_object

# Transformation
obj.location                      # Vector(x, y, z) — position
obj.rotation_euler                # Euler(x, y, z) — rotation en radians
obj.rotation_mode                 # 'XYZ', 'XZY', 'QUATERNION', etc.
obj.scale                         # Vector(x, y, z) — échelle
obj.dimensions                    # Vector(x, y, z) — dimensions réelles

# Données
obj.data                          # Données liées (Mesh, Camera, Light...)
obj.type                          # 'MESH', 'CAMERA', 'LIGHT', 'EMPTY', etc.
obj.name                          # Nom de l'objet
obj.parent                        # Objet parent
obj.users                         # Nombre de références

# Collections
obj.users_collection              # Collections contenant cet objet
bpy.context.collection.objects.link(obj)    # Ajouter à la collection
bpy.context.collection.objects.unlink(obj)  # Retirer de la collection

# Visibilité
obj.hide_viewport                 # Masquer dans la vue 3D
obj.hide_render                   # Masquer au rendu
obj.hide_get() / obj.hide_set(True)

# Verrouillage
obj.lock_location                 # Verrouiller la position (Vector de bools)
obj.lock_rotation
obj.lock_scale

# Propriétés custom
obj["custom_property"]            # Accès
obj["custom_property"] = value    # Écriture
del obj["custom_property"]        # Suppression

# Matériaux
obj.data.materials.append(mat)
obj.data.materials.clear()
obj.data.materials[0]             # Premier matériau
obj.active_material_index         # Index du matériau actif
obj.active_material               # Matériau actif

# Apply transforms
obj.select_set(True)              # Sélectionner
obj.select_set(False)             # Désélectionner
bpy.context.view_layer.objects.active = obj  # Définir comme actif
```

### Mesh (bpy.types.Mesh)

```python
mesh = obj.data  # ou bpy.data.meshes["Name"]

# Informations
mesh.vertices                      # Collection de Vertex
mesh.edges                         # Collection de Edge
mesh.polygons                      # Collection de Polygon (faces)
mesh.loop_triangles                # Triangles triangulés

# Opérations
mesh.update()                      # Mettre à jour après modification
mesh.calc_normals()                # Recalculer les normales
mesh.calc_loop_triangles()         # Convertir en triangles

# Vertex
vertex = mesh.vertices[0]
vertex.co                          # Vector(x, y, z) — position
vertex.normal                      # Vector(x, y, z) — normale

# Edge
edge = mesh.edges[0]
edge.vertices                      # (v1, v2) — indices des vertices
edge.index

# Polygon (face)
polygon = mesh.polygons[0]
polygon.vertices                   # Tuple d'indices
polygon.area                       # Aire
polygon.normal                     # Normale de la face
polygon.loop_indices               # Indices des loops

# Modifier un vertex
mesh.vertices[0].co = Vector((1, 2, 3))
```

### Créer un mesh from scratch

```python
mesh = bpy.data.meshes.new("MyMesh")
mesh.from_pydata(
    vertices,   # [(x,y,z), ...] ou [Vector(...), ...]
    edges,      # [(v1,v2), ...]
    faces       # [(v1,v2,v3,v4), ...]
)
mesh.update()
obj = bpy.data.objects.new("MyObject", mesh)
bpy.context.collection.objects.link(obj)
```

### Material (bpy.types.Material)

```python
mat = bpy.data.materials.new("Name")
mat.use_nodes = True               # Activer les nodes
nodes = mat.node_tree.nodes        # Nodes du matériau
links = mat.node_tree.links        # Liens entre nodes

# Node output
output_node = nodes.get("Material Output")
# Node principale
principled = nodes.get("Principled BSDF")

# Modifier les propriétés
principled.inputs["Base Color"].default_value = (1, 0, 0, 1)  # RGBA
principled.inputs["Metallic"].default_value = 0.8
principled.inputs["Roughness"].default_value = 0.2
principled.inputs["Alpha"].default_value = 1.0
principled.inputs["IOR"].default_value = 1.45
principled.inputs["Emission Strength"].default_value = 5.0
principled.inputs["Emission Color"].default_value = (1, 0.8, 0.4, 1)

# Appliquer un matériau
obj.data.materials.append(mat)
# ou
obj.data.materials.clear()
obj.data.materials.append(mat)
```

### Nodes communs

```python
# Créer un node
node = nodes.new('ShaderNodeBsdfPrincipled')   # Principled BSDF
node = nodes.new('ShaderNodeTexImage')          # Texture Image
node = nodes.new('ShaderNodeTexNoise')          # Texture Bruit
node = nodes.new('ShaderNodeTexChecker')        # Texture Checker
node = nodes.new('ShaderNodeTexVoronoi')        # Texture Voronoi
node = nodes.new('ShaderNodeTexEnvironment')    # HDRI Environment
node = nodes.new('ShaderNodeMath')              # Math
node = nodes.new('ShaderNodeMix')               # Mix (RGB ou valeur)
node = nodes.new('ShaderNodeMapping')           # Mapping
node = nodes.new('ShaderNodeTexCoord')          # Texture Coordinate
node = nodes.new('ShaderNodeOutputMaterial')    # Material Output
node = nodes.new('ShaderNodeBsdfGlass')         # Glass BSDF
node = nodes.new('ShaderNodeBsdfGlossy')        # Glossy BSDF
node = nodes.new('ShaderNodeBsdfDiffuse')       # Diffuse BSDF
node = nodes.new('ShaderNodeEmission')          # Emission
node = nodes.new('ShaderNodeTransparentBsdf')   # Transparent
node = nodes.new('ShaderNodeMixShader')         # Mix Shader
node = nodes.new('ShaderNodeAddShader')         # Add Shader
node = nodes.new('ShaderNodeValToRGB')          # ColorRamp
node = nodes.new('ShaderNodeRGB')               # RGB constant
node = nodes.new('ShaderNodeValue')             # Valeur constante
node = nodes.new('ShaderNodeTexImage')          # Image Texture
node = nodes.new('ShaderNodeHueSaturation')     # Hue/Saturation
node = nodes.new('ShaderNodeGamma')             # Gamma
node = nodes.new('ShaderNodeBrightContrast')    # Bright/Contrast
node = nodes.new('ShaderNodeInvert')            # Invert
node = nodes.new('ShaderNodeVolumePrincipled')  # Volume Principled

# Positionner un node
node.location = (0, 0)

# Connecter
links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])
links.new(noise.outputs['Fac'], colorramp.inputs['Fac'])
links.new(texture.outputs['Color'], principled.inputs['Base Color'])
```

### Camera (bpy.types.Camera)

```python
cam = bpy.data.cameras.new("Name")
cam.lens                           # Distance focale (mm)
cam.sensor_width                   # Largeur du capteur (mm)
cam.clip_start                     # Plan near
cam.clip_end                       # Plan far
cam.dof.use_dof                    # Activer Depth of Field
cam.dof.aperture_fstop             # Ouverture (f-stop)
cam.dof.focus_distance             # Distance de mise au point
cam.dof.aperture_blades            # Nombre de blades (bokeh)
cam.dof.aperture_ratio             # Ratio d'ouverture

# Créer un objet caméra
cam_obj = bpy.data.objects.new("Camera", cam)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj  # Définir comme caméra active

# Orientation de la caméra
cam_obj.rotation_euler = Euler((math.radians(60), 0, math.radians(45)))
```

### Light (bpy.types.Light)

```python
light = bpy.data.lights.new("Name", type='POINT')
light.color                        # (r, g, b) 0-1
light.energy                       # Puissance (W)
light.shadow_soft_size             # Taille de l'ombre (rayon)

# Types : 'POINT', 'SUN', 'SPOT', 'AREA'
light = bpy.data.lights.new("Name", type='SUN')
light.angle                        # Angle du soleil (radians)

# Spot
light = bpy.data.lights.new("Name", type='SPOT')
light.spot_size                    # Angle du cône (radians)
light.spot_blend                   # Transition douce

# Area
light = bpy.data.lights.new("Name", type='AREA')
light.size                         # Taille (m)
light.shape                        # 'SQUARE', 'RECTANGLE', 'DISK', 'ELLIPSE'

# Ombres
light.shadow_method                # 'RAY_SHADOW', 'NONE'
light.use_shadow                    # Activer/désactiver les ombres

# Créer un objet lumière
light_obj = bpy.data.objects.new("Light", light)
bpy.context.scene.collection.objects.link(light_obj)
light_obj.location = Vector((0, 0, 5))
```

### World (fond/environnement)

```python
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
bg_node.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1)
bg_node.inputs["Strength"].default_value = 0.5

# HDRI Environment
tree = world.node_tree
nodes = tree.nodes
links = tree.links

env_tex = nodes.new('ShaderNodeTexEnvironment')
env_tex.image = bpy.data.images.load("//hdri/studio.exr")

tex_coord = nodes.new('ShaderNodeTexCoord')
mapping = nodes.new('ShaderNodeMapping')

links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
links.new(mapping.outputs['Vector'], env_tex.inputs['Vector'])
links.new(env_tex.outputs['Color'], bg_node.inputs['Color'])
```

---

## bpy.ops — Opérateurs

### Principe

```python
# Appel basique
bpy.ops.mesh.primitive_cube_add()

# Avec paramètres
bpy.ops.mesh.primitive_cube_add(
    size=2,
    location=(0, 0, 0),
    rotation=(0, 0, 0)
)

# Vérifier si l'opérateur est disponible
bpy.ops.mesh.primitive_cube_add.poll()  # True/False
```

### Mesh — Ajouter des primitives

```python
# Cube
bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))

# Sphère
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16)

# Cylinder
bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=2, vertices=32)

# Cone
bpy.ops.mesh.primitive_cone_add(radius1=1, radius2=0, depth=2, vertices=32)

# Plane
bpy.ops.mesh.primitive_plane_add(size=2)

# Torus
bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.25)

# Ico Sphere
bpy.ops.mesh.primitive_ico_sphere_add(radius=1, subdivisions=2)

# Monkey (Suzanne)
bpy.ops.mesh.primitive_monkey_add(location=(0,0,0))

# Circle
bpy.ops.mesh.primitive_circle_add(radius=1, vertices=32, fill_type='NGON')

# Curve
bpy.ops.curve.primitive_bezier_circle_add(radius=1)
```

### Mesh — Édition

```python
# Tout sélectionner
bpy.ops.mesh.select_all(action='SELECT')

# Tout désélectionner
bpy.ops.mesh.select_all(action='DESELECT')

# Inverser la sélection
bpy.ops.mesh.select_all(action='INVERT')

# Extruder
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 2)})

# Bevel
bpy.ops.mesh.bevel(offset=0.1, segments=3)

# Loop cut
bpy.ops.mesh.loopcut_slide(
    TRANSFORM_OT_edge_slide={"factor": 0.5}
)

# Subdivide
bpy.ops.mesh.subdivide(number_cuts=2)

# Merge (fusionner)
bpy.ops.mesh.merge(type='CENTER')  # Au centre

# Delete
bpy.ops.mesh.delete(type='VERT')   # Supprimer les vertices sélectionnés
bpy.ops.mesh.delete(type='EDGE')   # Supprimer les arêtes
bpy.ops.mesh.delete(type='FACE')   # Supprimer les faces

# Smooth
bpy.ops.mesh.select_more()         # Étendre la sélection
bpy.ops.mesh.select_less()         # Réduire la sélection

# Normals
bpy.ops.mesh.normals_make_consistent(inside=False)

# Remove doubles
bpy.ops.mesh.remove_doubles(threshold=0.001)

# Mark seam (pour UV)
bpy.ops.mesh.mark_seam(clear=False)
bpy.ops.mesh.mark_seam(clear=True)

# Flip normals
bpy.ops.mesh.flip_normals()
```

### UV

```python
# Smart UV Project
bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)

# Project from view
bpy.ops.uv.project_from_view(camera_bounds=False, margin=0.1)

# Average Island Scale
bpy.ops.uv.average_islands_scale()

# Pack Islands
bpy.ops.uv.pack_islands(margin=0.001)

# Cube projection
bpy.ops.uv.cube_project(cube_size=2, margin=0.1)

# Cylinder projection
bpy.ops.uv.cylinder_project()

# Sphere projection
bpy.ops.uv.sphere_project()
```

### Transformations

```python
# Translate (déplacer)
bpy.ops.transform.translate(value=(1, 0, 0))

# Rotate (rotation)
bpy.ops.transform.rotate(value=math.radians(45), orient_axis='Z')

# Scale (mise à l'échelle)
bpy.ops.transform.resize(value=(2, 2, 2))

# Orientations
# 'GLOBAL', 'LOCAL', 'NORMAL', 'GIMBAL', 'VIEW', 'CURSOR'
bpy.ops.transform.translate(value=(0, 0, 1), orient_type='LOCAL')
```

### Object

```python
# Join (fusionner des objets)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()

# Separer
bpy.ops.mesh.separate(type='SELECTED')  # Sélection courante

# Set Origin
bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME')
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

# Smooth shading
bpy.ops.object.shade_smooth()
bpy.ops.object.shade_flat()

# Apply transforms
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Mode switching
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.object.mode_set(mode='SCULPT')
```

### Caméra

```python
# Ajouter une caméra
bpy.ops.object.camera_add(location=(0, -5, 2), rotation=(math.radians(75), 0, 0))

# Définir comme active
bpy.context.scene.camera = cam_obj
```

### Lumière

```python
# Ajouter une lumière
bpy.ops.object.light_add(type='POINT', location=(0, 0, 5))
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
bpy.ops.object.light_add(type='SPOT', location=(0, 0, 5))
bpy.ops.object.light_add(type='AREA', location=(0, 0, 5))
```

### Rendu

```python
# Rendu de l'image courante
bpy.ops.render.render()

# Rendu en animation
bpy.ops.render.render(animation=True)

# Render still
bpy.ops.render.render(write_still=True)
```

### Collection

```python
# Créer une collection
col = bpy.data.collections.new("MyCollection")
bpy.context.scene.collection.children.link(col)

# Ajouter un objet à une collection
col.objects.link(obj)

# Retirer un objet d'une collection
col.objects.unlink(obj)

# Activer une collection
bpy.context.view_layer.active_layer_collection = \
    bpy.context.view_layer.layer_collection.children["MyCollection"]
```

---

## Scène (bpy.types.Scene)

```python
scene = bpy.context.scene

# Paramètres de rendu
scene.render.engine = 'CYCLES'          # ou 'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = True     # Fond transparent
scene.render.image_settings.file_format = 'PNG'  # ou 'OPEN_EXR', 'JPEG'

# Cycles spécifique
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.cycles.device = 'GPU'             # ou 'CPU'
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.01

# Eevee spécifique
scene.eevee.taa_render_samples = 64
scene.eevee.use_ssr = True              # Screen-space reflections
scene.eevee.use_ssr_refraction = True
scene.eevee.use_bloom = True

# Frame / Animation
scene.frame_start = 1
scene.frame_end = 250
scene.frame_current = 1
scene.render.fps = 24

# Caméra active
scene.camera = cam_obj

# World (fond)
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
bg_node.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1)

# Color Management
scene.view_settings.view_transform = 'Filmic'  # ou 'AgX' (Blender 4.0+)
scene.view_settings.look = 'Medium High Contrast'

# Compositing
scene.use_nodes = True
tree = scene.node_tree

# Sequencer (audio)
scene.sequence_editor_create()
seq = scene.sequence_editor.sequences.new_sound(
    name="Audio",
    filepath="//audio/track.wav",
    channel=1,
    start_frame=1
)
```

---

## mathutils — Types mathématiques

### Vector

```python
from mathutils import Vector

v = Vector((1, 2, 3))           # 3D
v = Vector((1, 2))              # 2D

# Opérations
v + w                            # Addition
v - w                            # Soustraction
v * 2                            # Multiplication scalaire
v.dot(w)                         # Produit scalaire
v.cross(w)                       # Produit vectoriel (3D)
v.length                         # Longueur
v.length_squared                 # Longueur au carré
v.normalized                     # Vector normalisé
v.to_tuple()                     # (x, y, z)
v.x, v.y, v.z                   # Accès composantes
v.freeze()                       # Rendre immutable

# Conversion
Vector((1, 2, 3)).to_euler()     # → Euler
Vector((1, 2, 3)).to_matrix()    # → Matrix 4x4

# Distance
(v - w).length                   # Distance entre deux points
(v - w).normalized               # Direction normalisée
```

### Matrix

```python
from mathutils import Matrix

# Identité
m = Matrix.Identity(4)           # Matrice 4x4 identité

# Translation
m = Matrix.Translation((1, 2, 3))

# Rotation (radians)
m = Matrix.Rotation(math.radians(45), 4, 'Z')  # Autour de Z

# Échelle
m = Matrix.Scale(2, 4, (1, 0, 0))  # Échelle x2 sur X, matrice 4x4

# Combiner
m = loc_mat @ rot_mat @ scale_mat  # Ordre : Translation × Rotation × Échelle

# Appliquer à un objet
obj.matrix_world = m

# Inverser
m_inverted = m.inverted()

# Transposer
m_transposed = m.transposed()
```

### Euler / Quaternion

```python
from mathutils import Euler, Quaternion

# Euler (radians)
e = Euler((math.radians(90), 0, math.radians(45)), 'XYZ')

# Quaternion
q = Quaternion((1, 0, 0, 0))    # (w, x, y, z)
q = Euler((math.radians(90), 0, 0)).to_quaternion()

# Conversion
e.to_quaternion()
q.to_euler()

# Rotation autour d'un axe
q = Quaternion((0, 0, 1), math.radians(45))  # 45° autour de Z
```

---

## bmesh — Édition de mesh avancée

```python
import bmesh

# Créer un mesh avec bmesh (plus puissant)
mesh = bpy.data.meshes.new("ProceduralMesh")
bm = bmesh.new()

# Ajouter des vertices
v1 = bm.verts.new((0, 0, 0))
v2 = bm.verts.new((1, 0, 0))
v3 = bm.verts.new((1, 1, 0))
v4 = bm.verts.new((0, 1, 0))

# Créer une edge
e1 = bm.edges.new([v1, v2])

# Créer une face
bm.faces.new([v1, v2, v3, v4])

# Mettre à jour
bm.to_mesh(mesh)
bm.free()
mesh.update()

# Créer l'objet
obj = bpy.data.objects.new("ProceduralObj", mesh)
bpy.context.collection.objects.link(obj)

# Modifier un mesh existant
obj = bpy.context.active_object
bm = bmesh.new()
bm.from_mesh(obj.data)
# ... modifications ...
bm.to_mesh(obj.data)
bm.free()
obj.data.update()
```

---

## Patterns courants

### Setup de scène complet

```python
import bpy
import math
from mathutils import Vector

# Nettoyer la scène
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Supprimer les données orphelines
for mesh in bpy.data.meshes:
    bpy.data.meshes.remove(mesh)
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)
for cam in bpy.data.cameras:
    bpy.data.cameras.remove(cam)
for light in bpy.data.lights:
    bpy.data.lights.remove(light)

# Configurer le rendu
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.cycles.samples = 128
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 250  # 10s à 24fps

# Color Management
scene.view_settings.view_transform = 'Filmic'
scene.view_settings.look = 'Medium High Contrast'

# Ajouter un cube
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "MyCube"

# Ajouter une caméra
bpy.ops.object.camera_add(
    location=(7, -7, 5),
    rotation=(math.radians(60), 0, math.radians(45))
)
cam = bpy.context.active_object
scene.camera = cam

# Ajouter une lumière
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
sun = bpy.context.active_object
sun.data.energy = 5
```

### Animation simple

```python
import bpy
import math

obj = bpy.context.active_object

# Frame 1
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)

# Frame 50
obj.location = (5, 0, 3)
obj.keyframe_insert(data_path="location", frame=50)

# Modifier l'interpolation
for fcurve in obj.animation_data.action.fcurves:
    for kf in fcurve.keyframe_points:
        kf.interpolation = 'BEZIER'
        kf.handle_left_type = 'AUTO_CLAMPED'
        kf.handle_right_type = 'AUTO_CLAMPED'

# Loop infini
modifier = fcurve.modifiers.new(type='CYCLES')
modifier.mode_before = 'REPEAT'
modifier.mode_after = 'REPEAT'
```

### Matériel procédural

```python
import bpy

obj = bpy.context.active_object
mat = bpy.data.materials.new("ProceduralMat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Nettoyer les nodes par défaut
for node in nodes:
    nodes.remove(node)

# Créer les nodes
output = nodes.new('ShaderNodeOutputMaterial')
output.location = (400, 0)

principled = nodes.new('ShaderNodeBsdfPrincipled')
principled.location = (200, 0)

noise = nodes.new('ShaderNodeTexNoise')
noise.location = (-200, 0)
noise.inputs["Scale"].default_value = 5.0

colorramp = nodes.new('ShaderNodeValToRGB')
colorramp.location = (0, -100)

# Connecter
links.new(noise.outputs["Fac"], colorramp.inputs["Fac"])
links.new(colorramp.outputs["Color"], principled.inputs["Base Color"])
links.new(principled.outputs["BSDF"], output.inputs["Surface"])

# Appliquer
obj.data.materials.clear()
obj.data.materials.append(mat)
```

### Géométrie procédurale avec bmesh

```python
import bpy
import bmesh
import math

# Créer un mesh avec bmesh
mesh = bpy.data.meshes.new("ProceduralMesh")
bm = bmesh.new()

# Ajouter des vertices
v1 = bm.verts.new((0, 0, 0))
v2 = bm.verts.new((1, 0, 0))
v3 = bm.verts.new((1, 1, 0))
v4 = bm.verts.new((0, 1, 0))

# Créer une face
bm.faces.new([v1, v2, v3, v4])

# Mettre à jour
bm.to_mesh(mesh)
bm.free()
mesh.update()

# Créer l'objet
obj = bpy.data.objects.new("ProceduralObj", mesh)
bpy.context.collection.objects.link(obj)
```

### Constraints

```python
obj = bpy.context.active_object

# Track To (regarder une cible)
constraint = obj.constraints.new(type='TRACK_TO')
constraint.target = target_obj
constraint.track_axis = 'TRACK_Z'
constraint.up_axis = 'UP_Y'

# Copy Location
constraint = obj.constraints.new(type='COPY_LOCATION')
constraint.target = target_obj

# Copy Rotation
constraint = obj.constraints.new(type='COPY_ROTATION')
constraint.target = target_obj
constraint.target_space = 'LOCAL'
constraint.owner_space = 'LOCAL'

# Child Of
constraint = obj.constraints.new(type='CHILD_OF')
constraint.target = parent_obj

# IK (Inverse Kinematics)
constraint = bone.constraints.new(type='IK')
constraint.target = target_obj
constraint.chain_count = 2
```

### Modifiers

```python
obj = bpy.context.active_object

# Subdivision Surface
mod = obj.modifiers.new("Subsurf", 'SUBSURF')
mod.levels = 2
mod.render_levels = 3

# Solidify (épaisseur)
mod = obj.modifiers.new("Solidify", 'SOLIDIFY')
mod.thickness = 0.1

# Bevel
mod = obj.modifiers.new("Bevel", 'BEVEL')
mod.width = 0.05
mod.segments = 2

# Array
mod = obj.modifiers.new("Array", 'ARRAY')
mod.count = 3
mod.use_relative_offset = True
mod.relative_offset_displace = (1.5, 0, 0)

# Mirror
mod = obj.modifiers.new("Mirror", 'MIRROR')
mod.use_axis = (True, False, False)

# Boolean (union, différence, intersection)
mod = obj.modifiers.new("Boolean", 'BOOLEAN')
mod.operation = 'UNION'  # 'UNION', 'INTERSECT', 'DIFFERENCE'
mod.object = target_obj

# Cloth
mod = obj.modifiers.new("Cloth", 'CLOTH')

# Fluid
mod = obj.modifiers.new("Fluid", 'FLUID')

# Particle System
obj.particle_systems.new()
ps = obj.particle_systems[0]
ps.settings.count = 1000
```

### Drivers

```python
import bpy

# Rotation basée sur un custom property
obj["rotation_speed"] = 0.5

driver = obj.driver_add('rotation_euler', 2)  # Z rotation
driver.driver.type = 'SCRIPTED'
var = driver.driver.variables.new()
var.name = "speed"
var.type = 'SINGLE_PROP'
var.targets[0].id = obj
var.targets[0].data_path = '["rotation_speed"]'
driver.driver.expression = "frame * speed * 0.0174533"
```

---

## Erreurs courantes à éviter

1. **`bpy.data.objects.new()` nécessite un `link()`** :
   ```python
   obj = bpy.data.objects.new("Name", data)
   bpy.context.collection.objects.link(obj)  # OBLIGATOIRE
   ```

2. **`bpy.ops` nécessite le bon contexte** :
   ```python
   # Si vous êtes en mode édition, revenez en object d'abord
   bpy.ops.object.mode_set(mode='OBJECT')
   ```

3. **Les angles sont en radians** :
   ```python
   import math
   rotation = math.radians(45)  # PAS 45
   ```

4. **Les couleurs sont RGBA (0-1)** :
   ```python
   color = (1.0, 0.0, 0.0, 1.0)  # Rouge opaque
   # PAS (255, 0, 0, 255)
   ```

5. **`bpy.context` change selon le contexte** :
   ```python
   # En script, préférez bpy.data pour l'accès direct
   obj = bpy.data.objects["MyObj"]  # Plus fiable
   # bpy.context.active_object dépend du mode UI
   ```

6. **Supprimer avant de recréer** :
   ```python
   # Toujours nettoyer avant de créer
   if "MyObj" in bpy.data.objects:
       bpy.data.objects.remove(bpy.data.objects["MyObj"], do_unlink=True)
   ```

7. **Les strings doivent être courtes** :
   ```python
   # BON
   description = "dark alley, neon, rain"
   # MAUVAIS
   description = "A dark cyberpunk alley with neon lights reflecting on wet ground..."
   ```

8. **Pas de triple-quotes pour les descriptions longues** :
   ```python
   # BON
   obj.name = "Neon_Sign_Green"
   # MAUVAIS
   obj.name = "This is a green neon sign that is placed on the left wall"
   ```

9. **Utiliser `from_pydata` pour créer des meshes** :
   ```python
   # Plus rapide et fiable que d'ajouter des vertices un par un
   mesh.from_pydata(vertices, edges, faces)
   ```

10. **Toujours `mesh.update()` après modification** :
    ```python
    mesh.vertices[0].co = Vector((1, 2, 3))
    mesh.update()  # OBLIGATOIRE
    ```

11. **Ne pas imbriquer `bpy.ops.object.mode_set`** :
    ```python
    # MAUVAIS — peut causer des erreurs de contexte
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # BON — faire tout en mode édition d'un coup
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.object.mode_set(mode='OBJECT')
    ```

12. **Vérifier `poll()` avant d'appeler un opérateur** :
    ```python
    if bpy.ops.mesh.extrude_region_move.poll():
        bpy.ops.mesh.extrude_region_move(...)
    ```
