"""DeepBl4nder UE5 Server — REST API for Unreal Engine 5.

FastAPI server that communicates with the UE5 Editor via its Python API.
The server receives commands from DeepBl4nder's UE5Bridge and executes
them inside the UE5 Editor (headless mode).

Architecture:
  DeepBl4nder API → UE5Bridge → REST API (this server) → UE5 Python API → UE5 Editor

This server must run on a machine where UE5 is installed.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("ue5-server")

app = FastAPI(
    title="DeepBl4nder UE5 Server",
    description="REST API to control Unreal Engine 5 from DeepBl4nder",
    version="0.1.0",
)

UE5_EXE = os.environ.get("UE5_EXE", "/opt/UnrealEngine/Engine/Binaries/Linux/UnrealEditor-Cmd")
UE5_PROJECT = os.environ.get("UE5_PROJECT", "/ue5-projects/DeepBl4nder")

# Track render status
_render_status: dict[str, Any] = {"status": "idle", "progress": 0.0}

# Try to import unreal (only available inside UE5 Editor)
try:
    import unreal
    UNREAL_AVAILABLE = True
except ImportError:
    UNREAL_AVAILABLE = False
    logger.warning("unreal module not available — running in stub mode")


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
        "unreal_api_available": UNREAL_AVAILABLE,
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
    if UNREAL_AVAILABLE:
        try:
            unreal.EditorLevelLibrary.new_level(f"/Game/Levels/{req.name}")
            return {"status": "ok", "level": req.name, "template": req.template}
        except Exception as e:
            logger.error("Failed to create level: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "level": req.name, "template": req.template, "mode": "stub"}


class LevelDeleteRequest(BaseModel):
    name: str

@app.post("/level/delete")
async def delete_level(req: LevelDeleteRequest):
    """Delete a level."""
    logger.info("Deleting level: %s", req.name)
    if UNREAL_AVAILABLE:
        try:
            asset_path = f"/Game/Levels/{req.name}"
            unreal.EditorAssetLibrary.delete_asset(asset_path)
            return {"status": "ok", "level": req.name}
        except Exception as e:
            logger.error("Failed to delete level: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "level": req.name, "mode": "stub"}


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
    if UNREAL_AVAILABLE:
        try:
            task = unreal.AssetImportTask()
            task.set_editor_property('filename', req.source)
            task.set_editor_property('destination_path', req.destination)
            task.set_editor_property('automated', True)
            task.set_editor_property('replace_existing', True)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            if task.get_editor_property('result'):
                return {"status": "ok", "source": req.source, "destination": req.destination}
            else:
                error_messages = task.get_editor_property('error_messages')
                raise HTTPException(status_code=500, detail=f"Import failed: {error_messages}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to import asset: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "source": req.source, "destination": req.destination, "mode": "stub"}


class ActorCreateRequest(BaseModel):
    type: str
    name: str
    transform: dict[str, Any] | None = None
    asset: str = ""

@app.post("/actor/create")
async def create_actor(req: ActorCreateRequest):
    """Create an actor in the current level."""
    logger.info("Creating actor: %s (type=%s)", req.name, req.type)
    if UNREAL_AVAILABLE:
        try:
            actor_class = unreal.StaticMeshActor
            location = unreal.Vector(0, 0, 0)
            rotation = unreal.Rotator(0, 0, 0)

            if req.transform:
                loc = req.transform.get("location", [0, 0, 0])
                rot = req.transform.get("rotation", [0, 0, 0])
                location = unreal.Vector(loc[0], loc[1], loc[2])
                rotation = unreal.Rotator(rot[0], rot[1], rot[2])

            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, location, rotation)
            actor.set_actor_label(req.name)

            if req.asset:
                static_mesh = unreal.EditorAssetLibrary.load_asset(req.asset)
                if static_mesh and hasattr(actor, 'static_mesh_component'):
                    actor.static_mesh_component.set_static_mesh(static_mesh)

            return {"status": "ok", "actor": req.name, "type": req.type}
        except Exception as e:
            logger.error("Failed to create actor: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "actor": req.name, "type": req.type, "mode": "stub"}


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
    if UNREAL_AVAILABLE:
        try:
            mat_tools = unreal.AssetToolsHelpers.get_asset_tools()
            mat = mat_tools.create_asset(req.name, '/Game/Materials', unreal.Material, None)

            mat.set_editor_property('base_color', unreal.LinearColor(req.base_color[0], req.base_color[1], req.base_color[2], 1.0))
            mat.set_editor_property('metallic', req.metallic)
            mat.set_editor_property('roughness', req.roughness)

            if req.emission_color:
                mat.set_editor_property('emissive_color', unreal.LinearColor(req.emission_color[0], req.emission_color[1], req.emission_color[2], 1.0))
                mat.set_editor_property('emissive_brightness', req.emission_intensity)

            unreal.EditorAssetLibrary.save_asset(f"/Game/Materials/{req.name}")
            return {"status": "ok", "material": req.name}
        except Exception as e:
            logger.error("Failed to create material: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "material": req.name, "mode": "stub"}


class MaterialApplyRequest(BaseModel):
    actor: str
    material: str

@app.post("/material/apply")
async def apply_material(req: MaterialApplyRequest):
    """Apply a material to an actor."""
    logger.info("Applying material %s to actor %s", req.material, req.actor)
    if UNREAL_AVAILABLE:
        try:
            actors = unreal.EditorLevelLibrary.get_all_level_actors()
            target_actor = None
            for actor in actors:
                if actor.get_actor_label() == req.actor:
                    target_actor = actor
                    break

            if not target_actor:
                raise HTTPException(status_code=404, detail=f"Actor '{req.actor}' not found")

            mat = unreal.EditorAssetLibrary.load_asset(f"/Game/Materials/{req.material}")
            if not mat:
                raise HTTPException(status_code=404, detail=f"Material '{req.material}' not found")

            components = unreal.EditorUtilityLibrary.get_components_from_selected_actors([target_actor])
            for comp in components:
                if hasattr(comp, 'set_material'):
                    comp.set_material(0, mat)

            return {"status": "ok", "actor": req.actor, "material": req.material}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to apply material: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "actor": req.actor, "material": req.material, "mode": "stub"}


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
    if UNREAL_AVAILABLE:
        try:
            if req.use_lumen:
                unreal.ConsoleVariableLibrary.set_cvar("r.DynamicGlobalIllumination.Method", "1")
                unreal.ConsoleVariableLibrary.set_cvar("r.Lumen.TraceMeshSDFs", "1")
            else:
                unreal.ConsoleVariableLibrary.set_cvar("r.DynamicGlobalIllumination.Method", "0")

            for light_data in req.lights:
                light_type = light_data.get("type", "PointLight")
                name = light_data.get("name", "Light")
                intensity = light_data.get("intensity", 10.0)
                location = light_data.get("location", [0, 0, 300])
                color = light_data.get("color", [1.0, 1.0, 1.0])
                rotation = light_data.get("rotation", [0, 0, 0])

                if light_type == "DirectionalLight":
                    actor_class = unreal.DirectionalLight
                elif light_type == "SpotLight":
                    actor_class = unreal.SpotLight
                else:
                    actor_class = unreal.PointLight

                loc = unreal.Vector(location[0], location[1], location[2])
                rot = unreal.Rotator(rotation[0], rotation[1], rotation[2])

                light_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, loc, rot)
                light_actor.set_actor_label(name)

                light_component = light_actor.get_component_by_class(unreal.LightComponent)
                if light_component:
                    light_component.set_intensity(intensity)
                    light_component.set_light_color(unreal.LinearColor(color[0], color[1], color[2], 1.0))

            return {"status": "ok", "lights": len(req.lights), "lumen": req.use_lumen}
        except Exception as e:
            logger.error("Failed to setup lighting: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "lights": len(req.lights), "lumen": req.use_lumen, "mode": "stub"}


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
    if UNREAL_AVAILABLE:
        try:
            light_classes = {
                "DirectionalLight": unreal.DirectionalLight,
                "PointLight": unreal.PointLight,
                "SpotLight": unreal.SpotLight,
                "RectLight": unreal.RectLight,
            }
            actor_class = light_classes.get(req.type, unreal.PointLight)
            loc = unreal.Vector(req.location[0], req.location[1], req.location[2])

            light_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, loc)
            light_actor.set_actor_label(req.name)

            light_component = light_actor.get_component_by_class(unreal.LightComponent)
            if light_component:
                light_component.set_intensity(req.intensity)
                light_component.set_light_color(unreal.LinearColor(req.color[0], req.color[1], req.color[2], 1.0))
                light_component.set_attenuation_radius(req.attenuation_radius)

            return {"status": "ok", "light": req.name, "type": req.type}
        except Exception as e:
            logger.error("Failed to create light: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "light": req.name, "type": req.type, "mode": "stub"}


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
    if UNREAL_AVAILABLE:
        try:
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            level_sequence = asset_tools.create_asset(
                req.name, '/Game/Sequences', unreal.LevelSequence, None
            )
            if level_sequence:
                movie_scene = level_sequence.get_movie_scene()
                movie_scene.set_display_rate(req.fps)
                frame_rate = unreal.FrameRate(req.fps, 1)
                frame_range = unreal.FrameRange(0, req.duration_frames)
                movie_scene.set_display_rate(req.fps)
                unreal.EditorAssetLibrary.save_asset(f"/Game/Sequences/{req.name}")
                return {"status": "ok", "sequence": req.name, "frames": req.duration_frames}
            else:
                raise HTTPException(status_code=500, detail="Failed to create level sequence")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to setup sequencer: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "sequence": req.name, "frames": req.duration_frames, "mode": "stub"}


class CameraTrackRequest(BaseModel):
    sequence: str
    camera: str
    keyframes: list[dict[str, Any]]

@app.post("/sequencer/add_camera")
async def add_camera_track(req: CameraTrackRequest):
    """Add a camera track to the Sequencer."""
    logger.info("Adding camera track: %s to %s", req.camera, req.sequence)
    if UNREAL_AVAILABLE:
        try:
            sequence_asset = unreal.EditorAssetLibrary.load_asset(f"/Game/Sequences/{req.sequence}")
            if not sequence_asset:
                raise HTTPException(status_code=404, detail=f"Sequence '{req.sequence}' not found")

            camera_actor = None
            actors = unreal.EditorLevelLibrary.get_all_level_actors()
            for actor in actors:
                if actor.get_actor_label() == req.camera:
                    camera_actor = actor
                    break

            if not camera_actor:
                raise HTTPException(status_code=404, detail=f"Camera '{req.camera}' not found")

            binding = sequence_asset.add_possessable(camera_actor)
            camera_component = camera_actor.get_component_by_class(unreal.CameraComponent)
            if camera_component:
                transform_track = binding.add_track(unreal.MovieScenePropertyTrack)
                transform_track.set_property_name_and_path("Transform", "Transform")
                for kf in req.keyframes:
                    frame = kf.get("frame", 0)
                    loc = kf.get("location", [0, 0, 0])
                    rot = kf.get("rotation", [0, 0, 0])
                    transform = unreal.Transform(
                        unreal.Rotator(rot[0], rot[1], rot[2]),
                        unreal.Vector(loc[0], loc[1], loc[2]),
                        unreal.Vector(1, 1, 1)
                    )
                    section = transform_track.get_sections()[0]
                    section.add_key(unreal.FrameNumber(frame), transform)

            unreal.EditorAssetLibrary.save_asset(f"/Game/Sequences/{req.sequence}")
            return {"status": "ok", "camera": req.camera, "keyframes": len(req.keyframes)}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to add camera track: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "camera": req.camera, "keyframes": len(req.keyframes), "mode": "stub"}


class ActorTrackRequest(BaseModel):
    sequence: str
    actor: str
    property: str
    keyframes: list[dict[str, Any]]

@app.post("/sequencer/add_actor_track")
async def add_actor_track(req: ActorTrackRequest):
    """Add an actor animation track to the Sequencer."""
    logger.info("Adding actor track: %s.%s to %s", req.actor, req.property, req.sequence)
    if UNREAL_AVAILABLE:
        try:
            sequence_asset = unreal.EditorAssetLibrary.load_asset(f"/Game/Sequences/{req.sequence}")
            if not sequence_asset:
                raise HTTPException(status_code=404, detail=f"Sequence '{req.sequence}' not found")

            target_actor = None
            actors = unreal.EditorLevelLibrary.get_all_level_actors()
            for actor in actors:
                if actor.get_actor_label() == req.actor:
                    target_actor = actor
                    break

            if not target_actor:
                raise HTTPException(status_code=404, detail=f"Actor '{req.actor}' not found")

            binding = sequence_asset.add_possessable(target_actor)
            transform_track = binding.add_track(unreal.MovieScenePropertyTrack)
            transform_track.set_property_name_and_path(req.property, req.property)

            for kf in req.keyframes:
                frame = kf.get("frame", 0)
                value = kf.get("value", [0, 0, 0])
                section = transform_track.get_sections()[0]
                if isinstance(value, list) and len(value) == 3:
                    transform = unreal.Transform(
                        unreal.Rotator(0, 0, 0),
                        unreal.Vector(value[0], value[1], value[2]),
                        unreal.Vector(1, 1, 1)
                    )
                    section.add_key(unreal.FrameNumber(frame), transform)

            unreal.EditorAssetLibrary.save_asset(f"/Game/Sequences/{req.sequence}")
            return {"status": "ok", "actor": req.actor, "keyframes": len(req.keyframes)}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to add actor track: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "actor": req.actor, "keyframes": len(req.keyframes), "mode": "stub"}


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
    if UNREAL_AVAILABLE:
        try:
            mrq = unreal.MoviePipelineQueueSubsystem()
            job = mrq.get_queue().allocate_new_job()

            if req.sequence:
                sequence_asset = unreal.EditorAssetLibrary.load_asset(f"/Game/Sequences/{req.sequence}")
                if sequence_asset:
                    job.set_editor_property('sequence', sequence_asset)

            renderer = job.get_configuration().find_setting_by_class(unreal.MoviePipelineRenderPassSetting)
            if renderer:
                renderer.output_resolution = unreal.IntPoint(req.resolution[0], req.resolution[1])

            mrq.render_job(job)
            _render_status["status"] = "started"
            return {"status": "started", "output": req.output}
        except Exception as e:
            logger.error("Failed to start render: %s", e)
            _render_status["status"] = "error"
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "started", "output": req.output, "mode": "stub"}


@app.get("/render/status")
async def get_render_status():
    """Get the current render status."""
    if UNREAL_AVAILABLE:
        try:
            mrq = unreal.MoviePipelineQueueSubsystem()
            if mrq.is_rendering():
                _render_status["status"] = "rendering"
                _render_status["progress"] = mrq.get_render_percentage_complete()
            else:
                if _render_status["status"] == "rendering":
                    _render_status["status"] = "completed"
                    _render_status["progress"] = 100.0
        except Exception:
            pass
    return _render_status


@app.post("/render/cancel")
async def cancel_render():
    """Cancel the current render."""
    global _render_status
    logger.info("Cancelling render")
    if UNREAL_AVAILABLE:
        try:
            mrq = unreal.MoviePipelineQueueSubsystem()
            mrq.cancel_rendering()
        except Exception as e:
            logger.error("Failed to cancel render: %s", e)
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
    if UNREAL_AVAILABLE:
        try:
            unreal.ConsoleVariableLibrary.set_cvar(req.name, str(req.value))
            return {"status": "ok", "name": req.name, "value": req.value}
        except Exception as e:
            logger.error("Failed to set CVar: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "name": req.name, "value": req.value, "mode": "stub"}


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
    if UNREAL_AVAILABLE:
        try:
            for name, value in cvars.items():
                unreal.ConsoleVariableLibrary.set_cvar(name, value)
            return {"status": "ok", "preset": req.preset, "cvars": cvars}
        except Exception as e:
            logger.error("Failed to set quality preset: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "preset": req.preset, "cvars": cvars, "mode": "stub"}


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8080)
