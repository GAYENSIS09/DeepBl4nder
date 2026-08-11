---
name: texturing
description: Créer et appliquer les textures : albedo, roughness, normal, maps selon les besoins.
---

# Texturing

Produire des textures cohérentes avec le look voulu. Les textures donnent vie aux matériaux PBR.

## Types de maps

| Map | Canal | Usage | Format |
|-----|-------|-------|--------|
| **Base Color (Albedo)** | RGB | Couleur diffuse | PNG/TGA 8-bit |
| **Roughness** | Grayscale | Rugosité de surface | PNG 8-bit |
| **Normal** | RGB | Détails de surface | PNG/TGA 8-bit |
| **Height/Displacement** | Grayscale | Déformation géométrie | PNG 16-bit/EXR |
| **Metallic** | Grayscale | Zone métallique | PNG 8-bit |
| **Ambient Occlusion** | Grayscale | Ombres de contact | PNG 8-bit |
| **Emission** | RGB | Zones lumineuses | PNG 8-bit |
| **Alpha** | Grayscale | Transparence | PNG 8-bit |

## Résolutions standards

| Usage | Résolution | Budget mémoire |
|-------|-----------|----------------|
| Arrière-plan | 512x512 | 1 MB |
| Props simples | 1024x1024 | 4 MB |
| Props détaillés | 2048x2048 | 16 MB |
| Personnages | 4096x4096 | 64 MB |
| Environnement | 4096x4096 ou 8192x8192 | 64-256 MB |

### Règle
Commencer basse résolution (1024), augmenter uniquement si nécessaire.

## Textures procédurales (déterministes)

```python
import bpy

mat = bpy.data.materials.new(name="Procedural_Wood")
mat.use_nodes = True
tree = mat.node_tree
nodes = tree.nodes

# Noise Texture pour le bois
noise = nodes.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value = 5.0
noise.inputs['Detail'].default_value = 8.0
noise.inputs['Roughness'].default_value = 0.6

# ColorRamp pour les couleurs du bois
ramp = nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.3, 0.2, 0.1, 1)  # foncé
ramp.color_ramp.elements[1].color = (0.6, 0.45, 0.3, 1)  # clair

# Mapping pour étirer dans une direction
mapping = nodes.new('ShaderNodeMapping')
mapping.inputs['Scale'].default_value = (1, 1, 5)  # étirer en Z

tex_coord = nodes.new('ShaderNodeTexCoord')

# Connexions
tree.links.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
tree.links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
tree.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
```

### Avantages procédural
- **Déterministe** : même seed = même résultat.
- **Pas de UV** : utilise les coordonnées objet/du monde.
- **Reproductible** : même paramètres = même texture.
- **Économique** : pas de fichier image.

## Textures image (bake ou import)

```python
import bpy

# Charger une texture
img = bpy.data.images.load("//textures/wood_diffuse.png")

mat = bpy.data.materials.new(name="Image_Wood")
mat.use_nodes = True
tree = mat.node_tree

img_tex = tree.nodes.new('ShaderNodeTexImage')
img_tex.image = img
```

### Baking (cuisson)
```python
# Bake les textures procédurales en images
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.bake_type = 'DIFFUSE'
scene.render.bake.use_pass_direct = False
scene.render.bake.use_pass_indirect = False

# Sélectionner l'objet et le matériau
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Créer l'image cible
bake_img = bpy.data.images.new("baked_diffuse", width=2048, height=2048)

# Bake
bpy.ops.render.bake(type='DIFFUSE')
```

## Nommage des fichiers

```
textures/
├── <asset_name>/
│   ├── <asset>_diffuse.png      # Base color
│   ├── <asset>_roughness.png    # Roughness
│   ├── <asset>_normal.png       # Normal
│   ├── <asset>_height.png       # Height/Displacement
│   ├── <asset>_metallic.png     # Metallic
│   └── <asset>_ao.png           # Ambient Occlusion
```

## Application des textures

```python
import bpy

# Assigner un matériau à un objet
obj = bpy.data.objects["MyObject"]
mat = bpy.data.materials["MyMaterial"]
obj.data.materials.append(mat)

# Ou remplacer
obj.data.materials.clear()
obj.data.materials.append(mat)
```

## Optimisation

- **Texture Atlas** : combiner plusieurs petites textures en une grande.
- **Mipmapping** : Blender génère automatiquement les mipmaps.
- **Compression** : utiliser PNG (lossless) pour le rendu, JPG (lossy) pour les preview.
- **VRAM** : vérifier la mémoire GPU disponible (4-8 GB typique).

## Erreurs courantes

1. **Résolution trop haute** : textures de 8K pour un petit objet = gaspillage.
2. **Pas de normal map** : surface plate, pas de détails.
3. **UV non dépliées** : texture étirée, pas applicable.
4. **Mix de procédural et d'image** : incohérence si pas de bake.
5. **Oublier le roughness** : tout est miroir ou tout est mat.
6. **Fichiers non nommés** : confusion dans les projets complexes.

## Règles

- Couvrir les maps utiles : base color, roughness, normal, height selon le matériau.
- Bakes : préférer des textures procédurales déterministes (seed fixe) reproductibles.
- Respecter la résolution cible et le budget mémoire du pipeline.
- Tester le rendu d'un échantillon avant d'engager le look complet.
- Référencer les textures par chemin relatif et hash (provenance).
- Livrer un `TextureSet` typé : maps, résolution, chemins, hash.
