---
name: compositing
description: Assembler les passes de rendu : correction, profondeur, effets, étalonnage final.
---

# Compositing

Assembler le rendu en une image finale maîtrisée. Le compositing est l'étape où l'on affine le look sans rerendre.

## Passes de rendu disponibles

### Passes d'entrée (Cycles)
```python
scene = bpy.context.scene
scene.render.use_compositing = True
scene.render.layers["RenderLayer"].use_pass_combined = True
scene.render.layers["RenderLayer"].use_pass_z = True  # profondeur
scene.render.layers["RenderLayer"].use_pass_mist = True  # brouillard
scene.render.layers["RenderLayer"].use_pass_normal = True  # normals
scene.render.layers["RenderLayer"].use_pass_diffuse_direct = True
scene.render.layers["RenderLayer"].use_pass_diffuse_indirect = True
scene.render.layers["RenderLayer"].use_pass_glossy_direct = True
scene.render.layers["RenderLayer"].use_pass_shadow = True
scene.render.layers["RenderLayer"].use_pass_ao = True  # ambient occlusion
```

### Types de passes

| Pass | Contenu | Usage |
|------|---------|-------|
| **Combined** | Image finale composite | Sortie directe |
| **Depth (Z)** | Distance caméra-objet | DOF post-rendu, fog |
| **Mist** | Brouillard atmosphérique | Profondeur, séparation de plans |
| **Normal** | Orientation des surfaces | Relighting, edge detection |
| **Diffuse Direct** | Éclairage diffus direct | Ajustement par couche |
| **Glossy Direct** | Réflexions spéculaires | Ajustement des reflets |
| **Shadow** | Zones d'ombre | Renforcement des ombres |
| **AO** | Ambient occlusion | Contact shadows, definition |

## Setup Compositor de base

```python
import bpy

scene = bpy.context.scene
scene.use_nodes = True
tree = scene.node_tree
nodes = tree.nodes
links = tree.links

# Nettoyer
for node in nodes:
    nodes.remove(node)

# Nodes de base
render_layer = nodes.new('CompositorNodeRLayers')
composite = nodes.new('CompositorNodeComposite')
viewer = nodes.new('CompositorNodeViewer')

links.new(render_layer.outputs['Image'], composite.inputs['Image'])
links.new(render_layer.outputs['Image'], viewer.inputs['Image'])
```

## Corrections couleur

### Levels (niveaux)
```python
levels = nodes.new('CompositorNodeLevels')
links.new(render_layer.outputs['Image'], levels.inputs['Image'])
links.new(levels.outputs['Image'], composite.inputs['Image'])

# Ajuster les seuils
levels.inputs['Minimum'].default_value = (0.05, 0.05, 0.05, 1)  # noirs
levels.inputs['Maximum'].default_value = (0.95, 0.95, 0.95, 1)  # blancs
```

### RGB Curves (courbes)
```python
curves = nodes.new('CompositorNodeRGB')
curves.mapping.curves[0].points.new(0.3, 0.25)  # assombrir les shadows
curves.mapping.curves[0].points.new(0.7, 0.75)  # éclaircir les highlights
curves.update()
links.new(render_layer.outputs['Image'], curves.inputs['Image'])
links.new(curves.outputs['Image'], composite.inputs['Image'])
```

### Color Balance (balance des couleurs)
```python
balance = nodes.new('CompositorNodeColorBalance')
# Lift (shadows), Gamma (midtones), Gain (highlights)
balance.lift = (0.95, 0.95, 1.0)  # shadows légèrement froides
balance.gamma = (1.0, 1.0, 1.0)   # midtones neutres
balance.gain = (1.0, 0.98, 0.95)  # highlights légèrement chaudes
links.new(render_layer.outputs['Image'], balance.inputs['Image'])
links.new(balance.outputs['Image'], composite.inputs['Image'])
```

### Hue Saturation
```python
hs = nodes.new('CompositorNodeHueSat')
hs.inputs['Hue'].default_value = 1.0  # pas de décalage
hs.inputs['Saturation'].default_value = 1.1  # légèrement plus saturé
hs.inputs['Value'].default_value = 1.0
links.new(render_layer.outputs['Image'], hs.inputs['Image'])
links.new hs.outputs['Image'], composite.inputs['Image'])
```

## Effets

### Glare (bloom/halo)
```python
glare = nodes.new('CompositorNodeGlare')
glare.glare_type = 'FOG_GLOW'  # ou 'STREAKS', 'BLOOM'
glare.quality = 'HIGH'
glare.threshold = 0.8  # seuil de luminosité
glare.size = 6  # taille du glow
links.new(render_layer.outputs['Image'], glare.inputs['Image'])
links.new(glare.outputs['Image'], composite.inputs['Image'])
```

- **FOG_GLOW** : halo doux, naturel
- **BLOOM** : glow large, cinématique
- **STREAKS** : étoiles, reflets punktuals

### Defocus (DOF post-rendu)
```python
defocus = nodes.new('CompositorNodeDefocus')
defocus.inputs['Z'].default_value = 5.0  # distance focus en mètres
defocus.inputs['Noisy Z'].default_value = 0.0
defocus.use_circular = True
defocus.use_maxblur = True
defocus.maxblur = 20.0  # blur max en pixels
links.new(render_layer.outputs['Image'], defocus.inputs['Image'])
links.new(render_layer.outputs['Depth'], defocus.inputs['Z'])
links.new(defocus.outputs['Image'], composite.inputs['Image'])
```

### Vignette
```python
# Créer un masque circulaire
ellipse = nodes.new('CompositorNodeEllipseMask')
ellipse.width = 1.2
ellipse.height = 1.2

blur = nodes.new('CompositorNodeBlur')
blur.size_x = 200
blur.size_y = 200

mix = nodes.new('CompositorNodeMixRGB')
mix.blend_type = 'MULTIPLY'
mix.inputs['Fac'].default_value = 0.3  # intensité de la vignette

links.new(ellipse.outputs['Mask'], blur.inputs['Image'])
links.new(blur.outputs['Image'], mix.inputs[2])  # Image 2
links.new(render_layer.outputs['Image'], mix.inputs[1])  # Image 1
links.new(mix.outputs['Image'], composite.inputs['Image'])
```

## Chaîne de compositing complète

```python
# 1. Render Layer
render_layer = nodes.new('CompositorNodeRLayers')

# 2. Color Balance (correction primaire)
balance = nodes.new('CompositorNodeColorBalance')
links.new(render_layer.outputs['Image'], balance.inputs['Image'])

# 3. Glare (bloom)
glare = nodes.new('CompositorNodeGlare')
glare.glare_type = 'FOG_GLOW'
glare.threshold = 0.8
links.new(balance.outputs['Image'], glare.inputs['Image'])

# 4. Hue Saturation (saturation finale)
hs = nodes.new('CompositorNodeHueSat')
hs.inputs['Saturation'].default_value = 1.05
links.new(glare.outputs['Image'], hs.inputs['Image'])

# 5. Vignette
ellipse = nodes.new('CompositorNodeEllipseMask')
blur = nodes.new('CompositorNodeBlur')
blur.size_x = 200
blur.size_y = 200
mix = nodes.new('CompositorNodeMixRGB')
mix.blend_type = 'MULTIPLY'
mix.inputs['Fac'].default_value = 0.25
links.new(ellipse.outputs['Mask'], blur.inputs['Image'])
links.new(hs.outputs['Image'], mix.inputs[1])
links.new(blur.outputs['Image'], mix.inputs[2])

# 6. Composite final
composite = nodes.new('CompositorNodeComposite')
links.new(mix.outputs['Image'], composite.inputs['Image'])
```

## Étalonnage entre plans

- **同一 scène** : mêmes réglages de Color Balance entre plans adjacents.
- **Transitions** : adapter la luminosité/teinte pour les transitions jour/nuit.
- **Référence** : garder un "hero frame" pour comparaison.
- **Variation** : ne pas dépasser ±10% de luminosité ou ±5° de teinte entre plans adjacents.

## Erreurs courantes

1. **Abuser de Glare** : bloom partout = image "savonneuse".
2. **Saturation excessive** : couleurs qui "cassent" (> 1.5).
3. **Vignette trop forte** : coins noirs, perte de l'image.
4. **Pas de reference** : compositer à l'aveugle sans comparaison.
5. **Working en 8-bit** : banding, artefacts. Toujours travailler en EXR/float.
6. **Oublier le viewer** : ne pas pouvoir évaluer en temps réel.

## Règles

- Utiliser les passes (diffuse, direct, shadow, mist, depth) pour un contrôle précis.
- Travailler en EXR/PBR avant de dégrader en 8-bit pour l'export.
- Correction : balance, contraste, teinte par couche (shadows/midtones/highlights).
- Effets ciblés : glare (bloom), defocus (DOF), vignette — avec modération et intention.
- Étalonnage final cohérent entre les plans d'une même séquence.
- Sortir un `CompositeArtifact` versionné relié à son `RenderArtifact`.
- Toujours utiliser un Viewer node pour évaluer en temps réel.
- Chaîne de compositing reproductible (pas de réglages manuels sur le Viewer).
