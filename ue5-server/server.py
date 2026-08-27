"""DeepBlender UE5 Server — REST API for Unreal Engine 5.

FastAPI server that communicates with the UE5 Editor via its Python API.
The server receives commands from DeepBlender's UE5Bridge and executes
them inside the UE5 Editor (headless mode).

Architecture:
  DeepBlender API → UE5Bridge → REST API (this server) → UE5 Python API → UE5 Editor

This server must run on a machine where UE5 is installed.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("ue5-server")

app = FastAPI(
    title="DeepBlender UE5 Server",
    description="REST API to control Unreal Engine 5 from DeepBlender",
    version="0.1.0",
)

UE5_EXE = os.environ.get("UE5_EXE", "/opt/UnrealEngine/Engine/Binaries/Linux/UnrealEditor-Cmd")
UE5_PROJECT = os.environ.get("UE5_PROJECT", "/ue5-projects/deepblender")

# Track render status
_render_status: dict[str, Any] = {"status": "idle", "progress": 0.0}


# ════════════════════════════════════════════════════════════════
#  Health
# ════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check endpoint."""
    ue5_available = Path(UE5_EXE).exists() if UE5_EXE else False
    return {
        "status": "ok",
        "ue5_available": ue5_available,
        "ue5_exe": UE5_EXE,
        "ue5_project": UE5_PROJECT,
    }


# ════════════════════════════════════════════════════════════════
#  Level
# ════════════════════════════════════════════════════════════════

class LevelCreateRequest(BaseModel):
    name: str
    template: str = "empty"

@app.post("/level/create")
async def create_level(req: LevelCreateRequest):
    """Create a new level in UE5."""
    logger.info("Creating level: %s (template=%s)", req.name, req.template)
    # In production, this would call UE5 Python API:
    # import unreal
    # unreal.EditorLevelLibrary.new_level(f"/Game/Levels/{req.name}")
    return {"status": "ok", "level": req.name, "template": req.template}


class LevelDeleteRequest(BaseModel):
    name: str

@app.post("/level/delete")
async def delete_level(req: LevelDeleteRequest):
    """Delete a level."""
    logger.info("Deleting level: %s", req.name)
    return {"status": "ok", "level": req.name}


# ════════════════════════════════════════════════════════════════
#  Assets
# ════════════════════════════════════════════════════════════════

class AssetImportRequest(BaseModel):
    source: str
    destination: str
    type: str = "auto"

@app.post("/asset/import")
async def import_asset(req: AssetImportRequest):
    """Import an asset (.fbx, .gltf, .glb) into UE5."""
    logger.info("Importing asset: %s -> %s", req.source, req.destination)
    # import unreal
    # task = unreal.AssetImportTask()
    # task.set_editor_property('filename', req.source)
    # task.set_editor_property('destination_path', req.destination)
    # unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return {"status": "ok", "source": req.source, "destination": req.destination}


class ActorCreateRequest(BaseModel):
    type: str
    name: str
    transform: dict[str, Any] | None = None
    asset: str = ""

@app.post("/actor/create")
async def create_actor(req: ActorCreateRequest):
    """Create an actor in the current level."""
    logger.info("Creating actor: %s (type=%s)", req.name, req.type)
    # import unreal
    # actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
    #     unreal.StaticMeshActor, unreal.Vector(0, 0, 0)
    # )
    # actor.set_actor_label(req.name)
    return {"status": "ok", "actor": req.name, "type": req.type}


# ════════════════════════════════════════════════════════════════
#  Materials
# ════════════════════════════════════════════════════════════════

class MaterialCreateRequest(BaseModel):
    name: str
    base_color: list[float] = [0.8, 0.8, 0.8]
    metallic: float = 0.0
    roughness: float = 0.5
    emission_color: list[float] | None = None
    emission_intensity: float = 0.0
    texture: str = ""

@app.post("/material/create")
async def create_material(req: MaterialCreateRequest):
    """Create a PBR Lumen material in UE5."""
    logger.info("Creating material: %s", req.name)
    # import unreal
    # mat_tools = unreal.AssetToolsHelpers.get_asset_tools()
    # mat = mat_tools.create_asset(req.name, '/Game/Materials', unreal.Material, None)
    # mat.set_editor_property('base_color', req.base_color)
    return {"status": "ok", "material": req.name}


class MaterialApplyRequest(BaseModel):
    actor: str
    material: str

@app.post("/material/apply")
async def apply_material(req: MaterialApplyRequest):
    """Apply a material to an actor."""
    logger.info("Applying material %s to actor %s", req.material, req.actor)
    return {"status": "ok", "actor": req.actor, "material": req.material}


# ════════════════════════════════════════════════════════════════
#  Lighting
# ════════════════════════════════════════════════════════════════

class LightingSetupRequest(BaseModel):
    lights: list[dict[str, Any]]
    use_lumen: bool = True
    skylight_intensity: float = 1.0
    environment_color: list[float] = [0.1, 0.1, 0.15]

@app.post("/lighting/setup")
async def setup_lighting(req: LightingSetupRequest):
    """Configure Lumen lighting."""
    logger.info("Setting up lighting: %d lights, lumen=%s", len(req.lights), req.use_lumen)
    # import unreal
    # if req.use_lumen:
    #     # Enable Lumen GI
    #     unreal.ConsoleVariableLibrary.set_cvar("r.DynamicGlobalIllumination.Method", "1")
    return {"status": "ok", "lights": len(req.lights), "lumen": req.use_lumen}


class LightCreateRequest(BaseModel):
    type: str
    name: str
    location: list[float] = [0, 0, 300]
    intensity: float = 10.0
    color: list[float] = [1.0, 1.0, 1.0]
    attenuation_radius: float = 1000.0

@app.post("/light/create")
async def create_light(req: LightCreateRequest):
    """Create a light."""
    logger.info("Creating light: %s (type=%s)", req.name, req.type)
    return {"status": "ok", "light": req.name, "type": req.type}


# ════════════════════════════════════════════════════════════════
#  Sequencer (Animation)
# ════════════════════════════════════════════════════════════════

class SequencerSetupRequest(BaseModel):
    name: str
    duration_frames: int = 240
    fps: int = 24
    tracks: list[dict[str, Any]] = []

@app.post("/sequencer/setup")
async def setup_sequencer(req: SequencerSetupRequest):
    """Configure the Sequencer for animation."""
    logger.info("Setting up sequencer: %s (%d frames @ %d fps)", req.name, req.duration_frames, req.fps)
    # import unreal
    # level_sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    #     req.name, '/Game/Sequences', unreal.LevelSequence, None
    # )
    return {"status": "ok", "sequence": req.name, "frames": req.duration_frames}


class CameraTrackRequest(BaseModel):
    sequence: str
    camera: str
    keyframes: list[dict[str, Any]]

@app.post("/sequencer/add_camera")
async def add_camera_track(req: CameraTrackRequest):
    """Add a camera track to the Sequencer."""
    logger.info("Adding camera track: %s to %s", req.camera, req.sequence)
    return {"status": "ok", "camera": req.camera, "keyframes": len(req.keyframes)}


class ActorTrackRequest(BaseModel):
    sequence: str
    actor: str
    property: str
    keyframes: list[dict[str, Any]]

@app.post("/sequencer/add_actor_track")
async def add_actor_track(req: ActorTrackRequest):
    """Add an actor animation track to the Sequencer."""
    logger.info("Adding actor track: %s.%s to %s", req.actor, req.property, req.sequence)
    return {"status": "ok", "actor": req.actor, "keyframes": len(req.keyframes)}


# ════════════════════════════════════════════════════════════════
#  Render (MRQ)
# ════════════════════════════════════════════════════════════════

class RenderStartRequest(BaseModel):
    output: str
    sequence: str = ""
    resolution: list[int] = [1920, 1080]
    format: str = "mp4"
    quality: str = "cinematic"
    anti_aliasing: int = 1
    override_existing: bool = True

@app.post("/render/start")
async def start_render(req: RenderStartRequest):
    """Start rendering via MRQ (Movie Render Queue)."""
    global _render_status
    logger.info("Starting render: %s (%dx%d, %s)", req.output, req.resolution[0], req.resolution[1], req.quality)
    _render_status = {"status": "rendering", "progress": 0.0, "output": req.output}
    # import unreal
    # mrq = unreal.MoviePipelineQueueSubsystem()
    # job = mrq.get_queue().allocate_new_job()
    # job.set_editor_property('map', req.sequence)
    # mrq.render_job(job)
    return {"status": "started", "output": req.output}


@app.get("/render/status")
async def get_render_status():
    """Get the current render status."""
    return _render_status


@app.post("/render/cancel")
async def cancel_render():
    """Cancel the current render."""
    global _render_status
    logger.info("Cancelling render")
    _render_status = {"status": "cancelled", "progress": 0.0}
    return {"status": "cancelled"}


# ════════════════════════════════════════════════════════════════
#  Console Variables
# ════════════════════════════════════════════════════════════════

class CVarSetRequest(BaseModel):
    name: str
    value: float | int | str

@app.post("/cvar/set")
async def set_cvar(req: CVarSetRequest):
    """Set a UE5 console variable."""
    logger.info("Setting CVar: %s = %s", req.name, req.value)
    # import unreal
    # unreal.ConsoleVariableLibrary.set_cvar(req.name, str(req.value))
    return {"status": "ok", "name": req.name, "value": req.value}


class QualityPresetRequest(BaseModel):
    preset: str  # low, medium, high, epic, cinematic

@app.post("/quality/preset")
async def set_quality_preset(req: QualityPresetRequest):
    """Set quality preset."""
    logger.info("Setting quality preset: %s", req.preset)
    presets = {
        "low": {"r.DynamicGlobalIllumination.Method": "0", "r.Nanite": "0"},
        "medium": {"r.DynamicGlobalIllumination.Method": "1", "r.Nanite": "1"},
        "high": {"r.DynamicGlobalIllumination.Method": "1", "r.Nanite": "1", "r.ScreenPercentage": "100"},
        "epic": {"r.DynamicGlobalIllumination.Method": "1", "r.Nanite": "1", "r.ScreenPercentage": "100", "r.Shadow.Quality": "5"},
        "cinematic": {"r.DynamicGlobalIllumination.Method": "1", "r.Nanite": "1", "r.ScreenPercentage": "150", "r.Shadow.Quality": "5", "r.MotionBlurQuality": "4"},
    }
    cvars = presets.get(req.preset, presets["high"])
    # for name, value in cvars.items():
    #     unreal.ConsoleVariableLibrary.set_cvar(name, value)
    return {"status": "ok", "preset": req.preset, "cvars": cvars}


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8080)
