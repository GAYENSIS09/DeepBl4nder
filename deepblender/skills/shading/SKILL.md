---
name: shading
description: Construire les matériaux et le look dev : PBR, valeurs physiques, cohérence de scène.
---

# Shading

Configurer les matériaux pour un rendu physique et cohérent. Le shading détermine comment la lumière interagit avec les surfaces.

## Principes PBR (Physically Based Rendering)

### Valeurs physiques réalistes

| Matériau | Base Color (sRGB) | Roughness | Metalness |
|----------|-------------------|-----------|-----------|
| **Plastic blanc** | (0.8, 0.8, 0.8) | 0.4 | 0.0 |
| **Plastic noir** | (0.05, 0.05, 0.05) | 0.3 | 0.0 |
| **Bois clair** | (0.6, 0.45, 0.3) | 0.7 | 0.0 |
| **Bois foncé** | (0.3, 0.2, 0.1) | 0.6 | 0.0 |
| **Métal (acier)** | (0.5, 0.5, 0.5) | 0.3 | 1.0 |
| **Métal (or)** | (1.0, 0.76, 0.33) | 0.2 | 1.0 |
| **Verre** | (0.95, 0.95, 0.95) | 0.0 | 0.0 |
| **Eau** | (0.0, 0.3, 0.5) | 0.0 | 0.0 |
| **Béton** | (0.5, 0.5, 0.5) | 0.8 | 0.0 |
| **Cuir** | (0.2, 0.1, 0.05) | 0.5 | 0.0 |
| **Tissu** | (0.5, 0.5, 0.5) | 0.9 | 0.0 |
| **Peau** | (0.8, 0.6, 0.5) | 0.5 | 0.0 |

### Règles PBR

1. **Base Color** : uniquement la couleur diffuse, pas d'ombrage.
2. **Roughness** : 0 = miroir parfait, 1 = mat完全. La plupart des matériaux sont entre 0.3 et 0.8.
3. **Metalness** : 0 = diélectrique (plastic, bois), 1 = conducteur (métal). Pas de valeurs intermédiaires réalistes.
4. **IOR** : indice de réfraction. Verre = 1.45, Eau = 1.33, Diamant = 2.42.

## Node setup de base

```python
import bpy

mat = bpy.data.materials.new(name="Material_Base")
mat.use_nodes = True
tree = mat.node_tree
nodes = tree.nodes
links = tree.links

# Nettoyer
for node in nodes:
    nodes.remove(node)

# Output
output = nodes.new('ShaderNodeOutputMaterial')
output.location = (400, 0)

# Principled BSDF
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (0, 0)
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

# Paramètres
bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1)  # blanc
bsdf.inputs['Roughness'].default_value = 0.5
bsdf.inputs['Metallic'].default_value = 0.0
```

## Texture Coordinate + Mapping

```python
# Pour les textures image
tex_coord = nodes.new('ShaderNodeTexCoord')
tex_coord.location = (-600, 0)

mapping = nodes.new('ShaderNodeMapping')
mapping.location = (-400, 0)

links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

# Image Texture
img_tex = nodes.new('ShaderNodeTexImage')
img_tex.location = (-200, 0)
img_tex.image = bpy.data.images.load("//textures/diffuse.png")
links.new(mapping.outputs['Vector'], img_tex.inputs['Vector'])
links.new(img_tex.outputs['Color'], bsdf.inputs['Base Color'])
```

## Types de nœuds principaux

| Nœud | Usage |
|------|-------|
| **Principled BSDF** | PBR unifié (le plus utilisé) |
| **Diffuse BSDF** | Diffus simple (pas de spéculaire) |
| **Glossy BSDF** | Réflexion spéculaire |
| **Glass BSDF** | Verre, transparence |
| **Transparent BSDF** | Transparence pure |
| **Emission** | Matériau lumineux |
| **Mix Shader** | Combiner deux matériaux |
| **Add Shader** | Superposer deux matériaux |

## Matériaux courants

### Verre
```python
bsdf.inputs['Base Color'].default_value = (0.95, 0.95, 0.95, 1)
bsdf.inputs['Roughness'].default_value = 0.0
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['IOR'].default_value = 1.45
bsdf.inputs['Alpha'].default_value = 0.1  # transparence
mat.blend_method = 'BLEND'  # pour Eevee
```

### Metal
```python
bsdf.inputs['Base Color'].default_value = (0.5, 0.5, 0.5, 1)  # acier
bsdf.inputs['Roughness'].default_value = 0.3
bsdf.inputs['Metallic'].default_value = 1.0
```

### Eau
```python
bsdf.inputs['Base Color'].default_value = (0.0, 0.3, 0.5, 1)
bsdf.inputs['Roughness'].default_value = 0.0
bsdf.inputs['IOR'].default_value = 1.33
bsdf.inputs['Alpha'].default_value = 0.8
```

### Matériau émetant
```python
emission = nodes.new('ShaderNodeEmission')
emission.inputs['Color'].default_value = (1.0, 0.8, 0.4, 1)
emission.inputs['Strength'].default_value = 5.0
links.new(emission.outputs['Emission'], output.inputs['Surface'])
```

## Cohérence de scène

- **Même palette** : tous les matériaux d'une scène utilisent les mêmes teintes de base.
- **Roughness cohérent** : pas de contraste roughness excessif (sauf intention).
- **Metalness binaire** : soit 0 soit 1, pas de valeurs intermédiaires.
- **Reuse** : un matériau = un nœud group réutilisable. Pas de doublons.

## LookDev (validation)

```python
# Créer une sphère de référence avec le matériau
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(3, 0, 1))
ref = bpy.context.active_object
ref.name = "lookdev_sphere"
ref.data.materials.append(mat)

# Placer une light pour valider
bpy.ops.object.light_add(type='AREA', location=(2, -2, 3))
light = bpy.context.active_object
light.data.energy = 200
```

## Erreurs courantes

1. **Base Color > 1** : physically impossible, causé des artefacts.
2. **Roughness = 0** partout : tout est miroir, pas réaliste.
3. **Metalness intermédiaire** : les métaux ont metalness = 1, les diélectriques = 0.
4. **Pas d'apply scale** : textures étirées.
5. **Oublier IOR** : verre et eau avec IOR = 1.5 = pas réaliste.
6. **Trop de matériaux** : confusion, lent à rendre.

## Règles

- Base PBR : base color, roughness, metalness dans des plages réalistes.
- Éviter les valeurs extrêmes (base color > 1, roughness 0 partout).
- Relier les maps aux nœuds (texture coordinate → mapping → image texture).
- Utiliser la lumière pour valider le matériau (test sur une sphère de référence).
- Cohérence : un même matériau = même nœud/group réutilisé (asset de material).
- Livrer un `MaterialSpec` typé et un LookDev d'évaluation.
