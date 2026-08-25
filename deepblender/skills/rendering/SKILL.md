---
name: rendering
description: Paramétrer et lancer le rendu : engine, samples, format, color management, budget GPU.
---

# Rendu

Produire des images de qualité dans un budget de temps et de GPU maîtrisé.

## Choix du moteur

| Critère | Eevee | Cycles |
|---------|-------|--------|
| Vitesse | 10-100x plus rapide | Référence qualité |
| Cas d'usage | Pré-rendus, anims simples, assets | Rendu final, reflexions précises |
| Limitations | Pas de vrai GI, reflexions screen-space | Plus lent, bruit aux faibles samples |
| Disponibilité | Toujours (pas de GPU requis) | GPU recommandé (CUDA/OptiX/Metal) |

- **Eevee** : `scene.render.engine = 'BLENDER_EEVEE_NEXT'` (Blender 4.x+) ou `'BLENDER_EEVEE'` (3.x)
- **Cycles** : `scene.render.engine = 'CYCLES'`, préférer OptiX > CUDA > HIP selon GPU

## Configuration du rendu

### Résolution et format

```python
scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = True  # fond transparent si besoin
```

- **Résolutions standards** : 1920x1080 (Full HD), 2560x1440 (2K), 3840x2160 (4K)
- Pour des tests rapides : `resolution_percentage = 50` ou `25`
- Format de sortie : `scene.render.image_settings.file_format` = `'PNG'` (8-bit) ou `'OPEN_EXR'` (32-bit pour compositing)

### Echantillonnage (Cycles)

```python
# Pré-rendu (rapide, test)
scene.cycles.samples = 64
scene.cycles.preview_samples = 32

# Rendu final
scene.cycles.samples = 512
scene.cycles.preview_samples = 256

# Optimisations
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.01  # seuil de bruit acceptable
scene.cycles.use_denoising = True
```

- **Budget temps** : estimer `samples × time_per_sample × frame_count`
- Pour des animations : limiter à 128-256 samples avec denoising
- Pour des stills : 512-2048 samples selon la complexité de la scène

### Eevee (rapide)

```python
scene.render.engine = 'BLENDER_EEVEE_NEXT'
# Pas besoin de samples élevé
scene.eevee.taa_render_samples = 64  # suffisant pour la plupart des cas
scene.eevee.use_ssr = True  # screen-space reflections
scene.eevee.use_ssr_refraction = True
scene.eevee.use_bloom = True
```

### Color Management

```python
# AgX (Blender 4.0+) — meilleure gestion des hautes lumières
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'  # ou 'Medium Contrast', 'High Contrast'

# Filmic (Blender 3.x) — fallback
scene.view_settings.view_transform = 'Filmic'
scene.view_settings.look = 'Medium High Contrast'

# Blanc de référence
scene.display_settings.display_device = 'sRGB'
scene.sequencer_colorspace_settings.name = 'sRGB'
```

### Frame Range (animation)

```python
scene.frame_start = 1
scene.frame_end = 250  # 10 s à 25 fps
scene.render.fps = 24  # cinéma
# scene.render.fps = 30  # vidéo web
# scene.render.fps = 25  # PAL
```

### Sortie vidéo (FFmpeg)

```python
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
```

## Budget GPU et temps

- Estimer par frame : `(samples / 1000) × (resolution_x × resolution_y / 1e6) × complexity_factor`
- Facteurs de complexité : 1.0 (simple), 2.0 (métaux/verre), 4.0 (volumétrie, SSS)
- Pour une animation de 10 s à 25 fps (250 frames) : multiplier par frame_count
- Si budget dépassé : réduire samples, resolution_percentage, ou passer à Eevee

## Patterns courants

### CRITICAL: Output file path

**Always use ABSOLUTE paths** for `scene.render.filepath`. The context variable `render_dir` provides the correct directory.

```python
import os
render_dir = os.environ.get("DEEPBLENDER_RENDER_DIR", ".")  # or use the injected variable
scene.render.filepath = render_dir + "/output.mp4"
```

NEVER use relative paths with `//` prefix — they resolve to the .blend file location which does not exist in headless mode. This causes "No media file produced by Blender script" errors.

### Render still (image unique)

```python
scene.render.filepath = render_dir + "/still_001.png"
bpy.ops.render.render(write_still=True)
```

### Render animation

```python
scene.render.filepath = render_dir + "/frame_"
bpy.ops.render.render(animation=True)
```

### Render d'essai rapide

```python
# Sauvegarder les settings originaux
orig_samples = scene.cycles.samples
orig_res = scene.render.resolution_percentage

# Configurer pour test
scene.cycles.samples = 32
scene.render.resolution_percentage = 25
scene.render.filepath = render_dir + "/test_render.png"
bpy.ops.render.render(write_still=True)

# Restaurer
scene.cycles.samples = orig_samples
scene.render.resolution_percentage = orig_res
```

## Erreurs courantes

1. **Oublier `resolution_percentage = 100`** : rendu en demi-résolution par défaut
2. **Samples trop élevés pour Eevee** : Eevee n'utilise pas les samples de la même façon
3. **Pas de denoising** : images bruitées aux faibles samples
4. **Filepath relatif cassé** : utiliser un chemin ABSOLU dans `render_dir`, jamais `//` (résout vers le .blend qui n'existe pas en headless)
5. **Oublier `animation=True`** : ne rend qu'une frame au lieu de toute la séquence
6. **AgX inexistant sur Blender < 4.0** : vérifier la version avant d'utiliser

## Règles

- Choisir l'engine selon le compromis qualité/vitesse : Cycles pour le final, Eevee pour les tests.
- Commencer avec des samples bas (32-64) pour les tests, augmenter pour le final (256-2048).
- Toujours activer le denoising pour des samples < 256.
- Color management : fixer AgX (4.0+) ou Filmic (3.x) et le look dès le début.
- Format de sortie explicite (PNG pour stills, EXR pour compositing, FFmpeg H264 pour vidéo).
- Budget : estimer le coût par frame et vérifier que le total ne dépasse pas les contraintes.
- Lancer via BlenderBridge ; lire le résultat, vérifier l'image avant QA.
- Utiliser `resolution_percentage` pour les tests rapides au lieu de modifier la résolution.
