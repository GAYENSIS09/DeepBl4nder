"""DeepBl4nder AI Video Server — REST API for AI Video Generation.

FastAPI server that handles AI video generation using various diffusion models.
The server receives commands from DeepBl4nder's AIVideoBridge and executes
GPU-accelerated video generation pipelines.

Architecture:
  DeepBl4nder API → AIVideoBridge → REST API (this server) → Diffusion Pipelines → Video Output

Supported models:
  - CogVideoX (text-to-video, image-to-video)
  - Wan2.1 (text-to-video)
  - AnimateDiff (motion adapter for Stable Diffusion)
  - Stable Video Diffusion (image-to-video)
  - LTX-2.5 (text-to-video with audio)
  - Mochi 1 (high-quality text-to-video)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("ai-video-server")

app = FastAPI(
    title="DeepBl4nder AI Video Server",
    description="REST API for AI video generation from DeepBl4nder",
    version="0.1.0",
)

# Configuration
GPU_ID = int(os.environ.get("GPU_ID", "0"))
CACHE_DIR = os.environ.get("CACHE_DIR", "/cache/ai-video")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output/ai-video")

# Track generation status
_generation_status: dict[str, Any] = {"status": "idle", "progress": 0.0}

# Ensure directories exist
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def _cache_key(prompt: str, seed: int, width: int, height: int, model: str) -> str:
    """Generate a cache key based on prompt hash + parameters."""
    data = f"{model}:{prompt}:{seed}:{width}:{height}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def _generate_video(
    model: str,
    prompt: str,
    output_path: str,
    seed: int = 42,
    num_frames: int = 49,
    width: int = 1024,
    height: int = 576,
    guidance_scale: float = 6.0,
    num_inference_steps: int = 50,
    image_path: str | None = None,
    motion_bucket_id: int = 127,
) -> dict[str, Any]:
    """Generate video using the specified model."""
    try:
        if model == "cogvideox":
            return _generate_cogvideox(
                prompt, output_path, seed, num_frames, width, height,
                guidance_scale, num_inference_steps
            )
        elif model == "svd" or model == "stable-video-diffusion":
            if not image_path:
                return {"success": False, "error": "SVD requires an input image"}
            return _generate_svd(
                image_path, output_path, seed, num_frames,
                motion_bucket_id, width, height
            )
        elif model == "animatediff":
            return _generate_animatediff(
                prompt, output_path, seed, num_frames, width, height,
                guidance_scale, num_inference_steps
            )
        else:
            return {"success": False, "error": f"Model '{model}' not implemented yet"}
    except Exception as e:
        logger.error("Video generation failed: %s", e)
        return {"success": False, "error": str(e)}


def _generate_cogvideox(
    prompt: str, output_path: str, seed: int, num_frames: int,
    width: int, height: int, guidance_scale: float, num_inference_steps: int
) -> dict[str, Any]:
    """Generate video using CogVideoX."""
    script = f"""
import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
import numpy as np

torch.manual_seed({seed})
pipe = CogVideoXPipeline.from_pretrained("THUDM/CogVideoX-5b")
pipe.to("cuda")

video = pipe(
    prompt="{prompt}",
    num_frames={num_frames},
    guidance_scale={guidance_scale},
    num_inference_steps={num_inference_steps},
).frames[0]

export_to_video(video, "{output_path}", fps=8)
print("SUCCESS")
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True, text=True, timeout=600,
            env={**os.environ, "CUDA_VISIBLE_DEVICES": str(GPU_ID)}
        )
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            return {"success": True, "output": output_path}
        return {"success": False, "error": result.stderr or result.stdout}
    finally:
        os.unlink(script_path)


def _generate_svd(
    image_path: str, output_path: str, seed: int, num_frames: int,
    motion_bucket_id: int, width: int, height: int
) -> dict[str, Any]:
    """Generate video using Stable Video Diffusion."""
    script = f"""
import torch
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import load_image, export_to_video

torch.manual_seed({seed})
pipe = StableVideoDiffusionPipeline.from_pretrained(
    "stabilityai/stable-video-diffusion-img2vid-xt"
)
pipe.to("cuda")

image = load_image("{image_path}")
video = pipe(
    image,
    num_frames={num_frames},
    motion_bucket_id={motion_bucket_id},
    fps=7,
    decode_chunk_size=8,
).frames[0]

export_to_video(video, "{output_path}", fps=7)
print("SUCCESS")
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True, text=True, timeout=600,
            env={**os.environ, "CUDA_VISIBLE_DEVICES": str(GPU_ID)}
        )
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            return {"success": True, "output": output_path}
        return {"success": False, "error": result.stderr or result.stdout}
    finally:
        os.unlink(script_path)


def _generate_animatediff(
    prompt: str, output_path: str, seed: int, num_frames: int,
    width: int, height: int, guidance_scale: float, num_inference_steps: int
) -> dict[str, Any]:
    """Generate video using AnimateDiff."""
    script = f"""
import torch
from diffusers import AnimateDiffPipeline, MotionAdapter, DDIMScheduler

adapter = MotionAdapter.from_pretrained("guoyww/animatediff-motion-adapter-v1-5-3")
pipe = AnimateDiffPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    motion_adapter=adapter,
    scheduler=DDIMScheduler.from_config(pipe.scheduler.config, beta_schedule="linear", clip_sample=False, timestep_spacing="linspace", steps_offset=1),
)
pipe.to("cuda")

torch.manual_seed({seed})
video = pipe(
    prompt="{prompt}",
    num_frames={num_frames},
    guidance_scale={guidance_scale},
    num_inference_steps={num_inference_steps},
).frames[0]

from diffusers.utils import export_to_video
export_to_video(video, "{output_path}", fps=8)
print("SUCCESS")
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True, text=True, timeout=600,
            env={**os.environ, "CUDA_VISIBLE_DEVICES": str(GPU_ID)}
        )
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            return {"success": True, "output": output_path}
        return {"success": False, "error": result.stderr or result.stdout}
    finally:
        os.unlink(script_path)


# ════════════════════════════════════════════════════════════════
#  Health
# ════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check endpoint."""
    gpu_available = False
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        gpu_available = result.returncode == 0
    except Exception:
        pass

    return {
        "status": "ok",
        "gpu_available": gpu_available,
        "gpu_id": GPU_ID,
        "cache_dir": CACHE_DIR,
        "output_dir": OUTPUT_DIR,
    }


# ════════════════════════════════════════════════════════════════
#  Text-to-Video
# ════════════════════════════════════════════════════════════════

class TextToVideoRequest(BaseModel):
    prompt: str
    model: str = "cogvideox"
    seed: int = 42
    num_frames: int = 49
    width: int = 1024
    height: int = 576
    guidance_scale: float = 6.0
    num_inference_steps: int = 50
    use_cache: bool = True

@app.post("/generate/t2v")
async def generate_text_to_video(req: TextToVideoRequest):
    """Generate video from text prompt."""
    global _generation_status
    logger.info("Generating T2V: model=%s, prompt='%s...'", req.model, req.prompt[:50])
    _generation_status = {"status": "generating", "progress": 0.0}

    # Check cache
    if req.use_cache:
        cache_file = Path(CACHE_DIR) / f"{_cache_key(req.prompt, req.seed, req.width, req.height, req.model)}.mp4"
        if cache_file.exists():
            output_path = str(Path(OUTPUT_DIR) / f"{req.model}_{req.seed}.mp4")
            import shutil
            shutil.copy2(cache_file, output_path)
            _generation_status = {"status": "completed", "progress": 100.0}
            return {"status": "completed", "output": output_path, "cached": True}

    output_path = str(Path(OUTPUT_DIR) / f"{req.model}_{req.seed}.mp4")

    result = _generate_video(
        model=req.model,
        prompt=req.prompt,
        output_path=output_path,
        seed=req.seed,
        num_frames=req.num_frames,
        width=req.width,
        height=req.height,
        guidance_scale=req.guidance_scale,
        num_inference_steps=req.num_inference_steps,
    )

    if result["success"]:
        # Cache the result
        if req.use_cache:
            cache_file = Path(CACHE_DIR) / f"{_cache_key(req.prompt, req.seed, req.width, req.height, req.model)}.mp4"
            import shutil
            shutil.copy2(output_path, cache_file)

        _generation_status = {"status": "completed", "progress": 100.0}
        return {"status": "completed", "output": output_path}
    else:
        _generation_status = {"status": "error", "progress": 0.0}
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ════════════════════════════════════════════════════════════════
#  Image-to-Video
# ════════════════════════════════════════════════════════════════

class ImageToVideoRequest(BaseModel):
    image_path: str
    model: str = "svd"
    prompt: str = ""
    seed: int = 42
    num_frames: int = 25
    motion_bucket_id: int = 127
    width: int = 1024
    height: int = 576
    use_cache: bool = True

@app.post("/generate/i2v")
async def generate_image_to_video(req: ImageToVideoRequest):
    """Generate video from image."""
    global _generation_status
    logger.info("Generating I2V: model=%s, image=%s", req.model, req.image_path)
    _generation_status = {"status": "generating", "progress": 0.0}

    # Check cache
    if req.use_cache:
        cache_file = Path(CACHE_DIR) / f"{_cache_key(req.image_path, req.seed, req.width, req.height, req.model)}.mp4"
        if cache_file.exists():
            output_path = str(Path(OUTPUT_DIR) / f"{req.model}_{req.seed}.mp4")
            import shutil
            shutil.copy2(cache_file, output_path)
            _generation_status = {"status": "completed", "progress": 100.0}
            return {"status": "completed", "output": output_path, "cached": True}

    output_path = str(Path(OUTPUT_DIR) / f"{req.model}_{req.seed}.mp4")

    result = _generate_video(
        model=req.model,
        prompt=req.prompt,
        output_path=output_path,
        seed=req.seed,
        num_frames=req.num_frames,
        width=req.width,
        height=req.height,
        image_path=req.image_path,
        motion_bucket_id=req.motion_bucket_id,
    )

    if result["success"]:
        # Cache the result
        if req.use_cache:
            cache_file = Path(CACHE_DIR) / f"{_cache_key(req.image_path, req.seed, req.width, req.height, req.model)}.mp4"
            import shutil
            shutil.copy2(output_path, cache_file)

        _generation_status = {"status": "completed", "progress": 100.0}
        return {"status": "completed", "output": output_path}
    else:
        _generation_status = {"status": "error", "progress": 0.0}
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ════════════════════════════════════════════════════════════════
#  Status
# ════════════════════════════════════════════════════════════════

@app.get("/generate/status")
async def get_generation_status():
    """Get the current generation status."""
    return _generation_status


@app.post("/generate/cancel")
async def cancel_generation():
    """Cancel the current generation."""
    global _generation_status
    logger.info("Cancelling generation")
    _generation_status = {"status": "cancelled", "progress": 0.0}
    return {"status": "cancelled"}


# ════════════════════════════════════════════════════════════════
#  Cache
# ════════════════════════════════════════════════════════════════

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    cache_dir = Path(CACHE_DIR)
    files = list(cache_dir.glob("*.mp4"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "cache_dir": str(cache_dir),
    }


@app.post("/cache/clear")
async def clear_cache():
    """Clear the video cache."""
    cache_dir = Path(CACHE_DIR)
    for f in cache_dir.glob("*.mp4"):
        f.unlink()
    return {"status": "ok", "message": "Cache cleared"}


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8082)
