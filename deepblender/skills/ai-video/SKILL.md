---
name: ai-video
description: Génération vidéo par IA : CogVideoX, Wan2.1, AnimateDiff, Stable Video Diffusion.
---

# AI Video Generation

Générer des vidéos à partir de prompts textuels ou d'images de référence.

## Modèles disponibles

| Modèle        | Type         | VRAM    | Licence    | Qualité  | Usage                   |
|---------------|-------------|---------|------------|----------|-------------------------|
| CogVideoX     | T2V/I2V     | 16GB    | Apache 2.0 | Haute    | Scènes courtes, réalistes|
| Wan2.1        | T2V         | 24GB+   | Apache 2.0 | Très haute| Animations longues      |
| AnimateDiff   | Motion SD   | 8GB     | Apache 2.0 | Moyenne  | Extensions de SD        |
| SVD           | I2V         | 16GB    | Stability  | Haute    | Animation d'images      |
| LTX-2.5       | T2V+Audio   | 24GB+   | Apache 2.0 | Haute    | Vidéo + audio ensemble  |
| Mochi 1       | T2V         | 24GB    | Apache 2.0 | Très haute| Réalisme du mouvement   |

## Pipeline de génération

### Text-to-Video (CogVideoX)
```python
from diffusers import CogVideoXPipeline

pipe = CogVideoXPipeline.from_pretrained("THUDM/CogVideoX-5b")
pipe.to("cuda")

video = pipe(
    prompt="A cyberpunk alley at night, neon lights reflecting on wet pavement, rain falling",
    num_frames=49,
    guidance_scale=6.0,
    num_inference_steps=50,
).frames[0]

# Sauvegarder en MP4
export_to_video(video, "output.mp4", fps=8)
```

### Image-to-Video (SVD)
```python
from diffusers import StableVideoDiffusionPipeline

pipe = StableVideoDiffusionPipeline.from_pretrained(
    "stabilityai/stable-video-diffusion-img2vid-xt"
)
pipe.to("cuda")

image = load_image("reference.png")
video = pipe(
    image,
    num_frames=25,
    motion_bucket_id=127,  # Intensité du mouvement
    fps=7,
    decode_chunk_size=8,
).frames[0]
```

### Animation via AnimateDiff
```python
from diffusers import AnimateDiffPipeline, MotionAdapter

adapter = MotionAdapter.from_pretrained("guoyww/animatediff-motion-adapter-v1-5-3")
pipe = AnimateDiffPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    motion_adapter=adapter,
)
pipe.to("cuda")

video = pipe(
    prompt="A character walking through a magical forest",
    num_frames=16,
    guidance_scale=7.5,
).frames[0]
```

## Intégration avec Blender

### Workflow hybride : Blender + AI

```python
# 1. Blender génère la scène de base
# 2. AI enrichit les détails

import bpy

# Rendre un frame de référence
bpy.context.scene.render.filepath = render_dir + "/reference.png"
bpy.ops.render.render(write_still=True)

# 3. Envoyer le frame à AI pour animation
# (via API interne GPU worker)
ai_video = generate_ai_video(
    image_path=render_dir + "/reference.png",
    prompt="Camera slowly dollies forward, atmospheric fog",
    duration=4.0,
    fps=24,
)

# 4. Compositing : Blender base + AI overlay
# via FFmpeg
```

### Cas d'usage AI Video dans le pipeline

| Étape           | Mode        | Quand l'utiliser                    |
|-----------------|-------------|--------------------------------------|
| Previz          | AI only     | Brouillon rapide avant rendu 3D     |
| Effets spéciaux | AI overlay  | Explosions, météo, particules       |
| Transitions     | AI only     | Interludes entre scènes             |
| Contenu social  | AI only     | Clips courts (TikTok, Reels)        |
| Final           | Blender     | Toujours pour le rendu final        |

## Limites et mitigations

| Limite                  | Mitigation                                    |
|------------------------|-----------------------------------------------|
| Durée max 4-8s         | Générer plusieurs clips, assembler avec FFmpeg|
| Incohérence temporelle | Utiliser des seeds fixes, SVD pour stabilité  |
| Pas de contrôle caméra | Blender pour la caméra, AI pour les détails   |
| Qualité variable       | Multi-pass : AI → upscale → compositing       |
| Coût GPU élevé         | Cache des générations, mode previz basse rés.  |

## Cache et optimisation

```python
# Cache basé sur hash du prompt + seed
import hashlib

def cache_key(prompt: str, seed: int, width: int, height: int) -> str:
    data = f"{prompt}:{seed}:{width}:{height}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

# Vérifier le cache avant génération
cached = ai_video_cache.get(cache_key(prompt, seed, 1024, 576))
if cached:
    return cached

# Sinon générer et cacher
video = generate_ai_video(...)
ai_video_cache.set(cache_key(prompt, seed, 1024, 576), video, ttl=3600)
```

## Règles

- Utiliser AI Video pour le previz et les effets, JAMAIS pour le rendu final
- Blender reste le moteur principal pour la qualité professionnelle
- Toujours fixer le seed pour la reproductibilité
- Cacheer les générations pour éviter les coûts redondants
- Vérifier les licences (Apache 2.0 = OK commercial)
- Limiter la durée à 4-8s par clip AI
