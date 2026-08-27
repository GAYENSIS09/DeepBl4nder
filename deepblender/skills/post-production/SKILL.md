---
name: post-production
description: Color grading avance, LUT, film grain, lens flare, motion blur post-render.
---

# Post-Production

Traitement d'image et etalonnage couleur post-rendu.

## Pipeline post-production

```
Rendu Blender (EXR multi-pass)
  → Compositing (passes combinees)
    → Color Grading (LUT + curves)
      → Film Grain + Lens Effects
        → Export final (MP4/ProRes)
```

## Color Grading avec Python

### Niveaux de base

```python
import bpy

def setup_color_grading(scene_name: str):
    """Configure le color grading dans le compositor Blender."""
    scene = bpy.data.scenes[scene_name]
    scene.use_nodes = True
    tree = scene.node_tree
    
    # Nodes de grading
    # 1. Exposure
    exposure = tree.nodes.new('CompositorNodeExposure')
    exposure.exposure = 0.0
    
    # 2. Color Balance (Lift/Gamma/Gain)
    color_balance = tree.nodes.new('CompositorNodeColorBalance')
    color_balance.correction_method = 'LIFT_GAMMA_GAIN'
    color_balance.lift = (0.02, 0.02, 0.03)  # Ombres legerement bleutees
    color_balance.gamma = (1.0, 0.98, 0.95)   # Midtons legerement chauds
    color_balance.gain = (1.05, 1.0, 0.95)    # Hautes lueurs legerement froides
    
    # 3. Curves (contraste)
    curves = tree.nodes.new('CompositorNodeRGBCurves')
    # Courbe S pour contraste
    curves.mapping.curves[0].points.new(0.25, 0.20)  # Assombrir les ombres
    curves.mapping.curves[0]. points.new(0.75, 0.80)  # Eclaircir les hautes
    
    return tree
```

### Application de LUT

```python
def apply_lut(node_tree, lut_path: str):
    """Applique un LUT 3D au compositor."""
    lut_node = node_tree.nodes.new('CompositorNodeImage')
    
    # Charger le LUT (format .cube ou .3dl)
    import numpy as np
    
    # Parser le fichier .cube
    lut_data = parse_cube_lut(lut_path)
    
    # Creer une image 3D pour le LUT
    size = lut_data['size']
    lut_image = bpy.data.images.new(
        name="LUT_3D",
        width=size * size,
        height=size,
        alpha=False,
        float_buffer=True,
    )
    
    # Remplir les donnees
    pixels = list(lut_data['data'].flatten())
    lut_image.pixels = pixels
    
    return lut_node
```

## LUT populaires

| Style           | LUT                | Usage                    |
|-----------------|--------------------|--------------------------|
| Cinematique     | Orange & Teal      | Films d'action           |
| Chaleureux      | Warm Film          | Dramatique, romance      |
| Froid           | Cold Blue          | Sci-fi, thriller         |
| Noir & Blanc    | B&W High Contrast  | Art, documentary         |
| Vintage         | Film Stock 70s     | Retro, nostalgie         |
| Neon            | Cyberpunk          | Sci-fi, futuriste        |

## Film Grain

```python
def add_film_grain(compositor_tree, amount: float = 0.02):
    """Ajoute du grain de film au rendu."""
    # Node bruit
    noise = compositor_tree.nodes.new('CompositorNodeTexture')
    noise.texture = bpy.data.textures.new("FilmGrain", 'VORONOI')
    noise.texture.noise_scale = 0.5
    
    # Mélanger avec le rendu
    mix = compositor_tree.nodes.new('CompositorNodeMixRGB')
    mix.blend_type = 'OVERLAY'
    mix.inputs[0].default_value = amount  # Intensite du grain
    
    return noise, mix
```

## Lens Effects

```python
def add_lens_flare(compositor_tree, position: tuple[float, float] = (0.5, 0.5)):
    """Ajoute un lens flare positionne."""
    flare = compositor_tree.nodes.new('CompositorNodeLensdist')
    flare.inputs['Dispersion'].default_value = 0.01
    flare.use_jitter = True
    return flare

def add_vignette(compositor_tree, strength: float = 0.3):
    """Ajoute un vignettage."""
    # Ellipse masque
    ellipse = compositor_tree.nodes.new('CompositorNodeEllipseMask')
    ellipse.width = 0.8
    ellipse.height = 0.8
    
    # Flou gaussien
    blur = compositor_tree.nodes.new('CompositorNodeBlur')
    blur.size_x = 200
    blur.size_y = 200
    
    # Inverser et multiplier
    invert = compositor_tree.nodes.new('CompositorNodeInvert')
    
    multiply = compositor_tree.nodes.new('CompositorNodeMixRGB')
    multiply.blend_type = 'MULTIPLY'
    multiply.inputs[0].default_value = strength
    
    return ellipse, blur, invert, multiply
```

## Motion Blur post-render

```python
def apply_motion_blur(ffmpeg_cmd: str, blur_amount: float = 0.5):
    """Applique un motion blur via FFmpeg post-render."""
    # FFmpeg vector de deplacement
    cmd = (
        f"{ffmpeg_cmd} "
        f"-vf \"minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:vsbmc=1\" "
        f"-frames:v 1"
    )
    return cmd
```

## Export multi-format

```python
EXPORT_PRESETS = {
    "mp4_h264": {
        "format": "MPEG4",
        "codec": "H264",
        "quality": "MEDIUM",
        "bitrate": "8M",
    },
    "prores": {
        "format": "QUICKTIME",
        "codec": "PRORES",
        "quality_lossless": True,
    },
    "exr": {
        "format": "OPEN_EXR",
        "codec": "ZIP",
        "depth": "16",
    },
    "webm_vp9": {
        "format": "WEBM",
        "codec": "VP9",
        "quality": "GOOD",
        "bitrate": "4M",
    },
}

def export_final(scene_name: str, preset: str = "mp4_h264"):
    """Exporte le rendu final avec le preset choisi."""
    config = EXPORT_PRESETS.get(preset, EXPORT_PRESETS["mp4_h264"])
    scene = bpy.data.scenes[scene_name]
    
    scene.render.image_settings.file_format = config["format"]
    if "codec" in config:
        scene.render.ffmpeg.codec = config["codec"]
    if "quality" in config:
        scene.render.ffmpeg.constant_rate_factor = config["quality"]
```

## Regles

- Toujours travailler en EXR pour le grading (pas de perte)
- Appliquer le LUT AVANT le grain de film
- Vigneretting en dernier (apres tous les effets)
- Exporter en ProRes pour le mastering, H264 pour le web
- Tester le grading sur plusieurs ecrans
- Garder les nodes de grading modifiables (non flattened)
