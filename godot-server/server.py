"""DeepBl4nder Godot Server — REST API for Godot 4 Engine.

FastAPI server that communicates with Godot 4 via its command-line interface.
The server receives commands from DeepBl4nder's GodotBridge and executes
GDScript commands in Godot headless mode.

Architecture:
  DeepBl4nder API → GodotBridge → REST API (this server) → Godot CLI → GDScript execution
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("godot-server")

app = FastAPI(
    title="DeepBl4nder Godot Server",
    description="REST API to control Godot 4 from DeepBl4nder",
    version="0.1.0",
)

GODOT_EXE = os.environ.get("GODOT_EXE", "/usr/local/bin/godot")
GODOT_PROJECT = os.environ.get("GODOT_PROJECT", "/godot-projects/DeepBl4nder")

# Track render status
_render_status: dict[str, Any] = {"status": "idle", "progress": 0.0}


def _run_godot_script(script_code: str, args: list[str] | None = None) -> dict[str, Any]:
    """Execute a GDScript in Godot headless mode."""
    godot_path = Path(GODOT_EXE)
    if not godot_path.exists():
        return {"success": False, "error": f"Godot not found at {GODOT_EXE}"}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".gd", delete=False, dir="/tmp"
    ) as f:
        f.write(script_code)
        script_path = f.name

    try:
        cmd = [
            GODOT_EXE,
            "--headless",
            "--path", GODOT_PROJECT,
            "--script", script_path,
        ]
        if args:
            cmd.extend(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            try:
                output = json.loads(result.stdout)
                return {"success": True, "output": output}
            except json.JSONDecodeError:
                return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or result.stdout}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Godot script execution timed out"}
    except FileNotFoundError:
        return {"success": False, "error": f"Godot executable not found: {GODOT_EXE}"}
    finally:
        os.unlink(script_path)


# ════════════════════════════════════════════════════════════════
#  Health
# ════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check endpoint."""
    godot_available = Path(GODOT_EXE).exists() if GODOT_EXE else False
    return {
        "status": "ok",
        "godot_available": godot_available,
        "godot_exe": GODOT_EXE,
        "godot_project": GODOT_PROJECT,
    }


# ════════════════════════════════════════════════════════════════
#  Scene
# ════════════════════════════════════════════════════════════════

class SceneCreateRequest(BaseModel):
    name: str
    description: str = ""

@app.post("/scene/create")
async def create_scene(req: SceneCreateRequest):
    """Create a new scene in Godot."""
    logger.info("Creating scene: %s", req.name)
    script = f"""
extends SceneTree

func _init():
    var root = Node3D.new()
    root.name = "{req.name}"
    var scene_packed = PackedScene.new()
    scene_packed.pack(root)
    ResourceSaver.save("res://{req.name}.tscn", scene_packed)
    print(json.dumps({{"status": "ok", "scene": "{req.name}"}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "scene": req.name}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


class SceneDeleteRequest(BaseModel):
    name: str

@app.post("/scene/delete")
async def delete_scene(req: SceneDeleteRequest):
    """Delete a scene."""
    logger.info("Deleting scene: %s", req.name)
    scene_path = Path(GODOT_PROJECT) / f"{req.name}.tscn"
    if scene_path.exists():
        scene_path.unlink()
    return {"status": "ok", "scene": req.name}


# ════════════════════════════════════════════════════════════════
#  Mesh
# ════════════════════════════════════════════════════════════════

class MeshCreateRequest(BaseModel):
    name: str
    type: str = "cube"  # cube, sphere, plane, cylinder, capsule
    size: list[float] = [1.0, 1.0, 1.0]
    position: list[float] = [0.0, 0.0, 0.0]

@app.post("/mesh/create")
async def create_mesh(req: MeshCreateRequest):
    """Create a mesh in the scene."""
    logger.info("Creating mesh: %s (type=%s)", req.name, req.type)
    mesh_types = {
        "cube": "BoxMesh",
        "sphere": "SphereMesh",
        "plane": "PlaneMesh",
        "cylinder": "CylinderMesh",
        "capsule": "CapsuleMesh",
    }
    mesh_class = mesh_types.get(req.type, "BoxMesh")

    script = f"""
extends SceneTree

func _init():
    var root = Node3D.new()
    var mesh_instance = MeshInstance3D.new()
    mesh_instance.name = "{req.name}"
    mesh_instance.mesh = {mesh_class}.new()
    mesh_instance.position = Vector3({req.position[0]}, {req.position[1]}, {req.position[2]})
    root.add_child(mesh_instance)
    var scene_packed = PackedScene.new()
    scene_packed.pack(root)
    ResourceSaver.save("res://current_scene.tscn", scene_packed)
    print(json.dumps({{"status": "ok", "mesh": "{req.name}", "type": "{req.type}"}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "mesh": req.name, "type": req.type}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ════════════════════════════════════════════════════════════════
#  Material
# ════════════════════════════════════════════════════════════════

class MaterialCreateRequest(BaseModel):
    name: str
    base_color: list[float] = [0.8, 0.8, 0.8]
    metallic: float = 0.0
    roughness: float = 0.5
    emission_color: list[float] | None = None
    emission_energy: float = 0.0

@app.post("/material/create")
async def create_material(req: MaterialCreateRequest):
    """Create a PBR material in Godot."""
    logger.info("Creating material: %s", req.name)
    emission_code = ""
    if req.emission_color:
        emission_code = f"""
    mat.emission_enabled = true
    mat.emission = Color({req.emission_color[0]}, {req.emission_color[1]}, {req.emission_color[2]})
    mat.emission_energy_multiplier = {req.emission_energy}
"""

    script = f"""
extends SceneTree

func _init():
    var mat = StandardMaterial3D.new()
    mat.albedo_color = Color({req.base_color[0]}, {req.base_color[1]}, {req.base_color[2]})
    mat.metallic = {req.metallic}
    mat.roughness = {req.roughness}
    {emission_code}
    ResourceSaver.save("res://materials/{req.name}.tres", mat)
    print(json.dumps({{"status": "ok", "material": "{req.name}"}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "material": req.name}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


class MaterialApplyRequest(BaseModel):
    mesh: str
    material: str

@app.post("/material/apply")
async def apply_material(req: MaterialApplyRequest):
    """Apply a material to a mesh."""
    logger.info("Applying material %s to mesh %s", req.material, req.mesh)
    script = f"""
extends SceneTree

func _init():
    var scene = load("res://current_scene.tscn").instantiate()
    var mesh = scene.get_node("{req.mesh}")
    if mesh:
        var mat = load("res://materials/{req.material}.tres")
        if mat:
            mesh.material_override = mat
    var scene_packed = PackedScene.new()
    scene_packed.pack(scene)
    ResourceSaver.save("res://current_scene.tscn", scene_packed)
    print(json.dumps({{"status": "ok", "mesh": "{req.mesh}", "material": "{req.material}"}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "mesh": req.mesh, "material": req.material}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ════════════════════════════════════════════════════════════════
#  Camera
# ════════════════════════════════════════════════════════════════

class CameraCreateRequest(BaseModel):
    name: str
    position: list[float] = [0.0, 3.0, 8.0]
    look_at: list[float] = [0.0, 1.0, 0.0]
    fov: float = 75.0

@app.post("/camera/create")
async def create_camera(req: CameraCreateRequest):
    """Create a camera in the scene."""
    logger.info("Creating camera: %s", req.name)
    script = f"""
extends SceneTree

func _init():
    var scene = load("res://current_scene.tscn").instantiate()
    var camera = Camera3D.new()
    camera.name = "{req.name}"
    camera.position = Vector3({req.position[0]}, {req.position[1]}, {req.position[2]})
    camera.look_at(Vector3({req.look_at[0]}, {req.look_at[1]}, {req.look_at[2]}))
    camera.fov = {req.fov}
    scene.add_child(camera)
    var scene_packed = PackedScene.new()
    scene_packed.pack(scene)
    ResourceSaver.save("res://current_scene.tscn", scene_packed)
    print(json.dumps({{"status": "ok", "camera": "{req.name}"}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "camera": req.name}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ════════════════════════════════════════════════════════════════
#  Lighting
# ════════════════════════════════════════════════════════════════

class LightCreateRequest(BaseModel):
    type: str = "directional"  # directional, omni, spot
    name: str = "Light"
    position: list[float] = [0.0, 3.0, 0.0]
    rotation: list[float] = [-45.0, 0.0, 0.0]
    energy: float = 2.0
    color: list[float] = [1.0, 1.0, 1.0]

@app.post("/light/create")
async def create_light(req: LightCreateRequest):
    """Create a light in the scene."""
    logger.info("Creating light: %s (type=%s)", req.name, req.type)
    light_classes = {
        "directional": "DirectionalLight3D",
        "omni": "OmniLight3D",
        "spot": "SpotLight3D",
    }
    light_class = light_classes.get(req.type, "DirectionalLight3D")

    script = f"""
extends SceneTree

func _init():
    var scene = load("res://current_scene.tscn").instantiate()
    var light = {light_class}.new()
    light.name = "{req.name}"
    light.position = Vector3({req.position[0]}, {req.position[1]}, {req.position[2]})
    light.rotation_degrees = Vector3({req.rotation[0]}, {req.rotation[1]}, {req.rotation[2]})
    light.light_energy = {req.energy}
    light.light_color = Color({req.color[0]}, {req.color[1]}, {req.color[2]})
    scene.add_child(light)
    var scene_packed = PackedScene.new()
    scene_packed.pack(scene)
    ResourceSaver.save("res://current_scene.tscn", scene_packed)
    print(json.dumps({{"status": "ok", "light": "{req.name}", "type": "{req.type}"}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "light": req.name, "type": req.type}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


class LightingSetupRequest(BaseModel):
    lights: list[dict[str, Any]]
    use_glow: bool = True
    ambient_light_energy: float = 0.3

@app.post("/lighting/setup")
async def setup_lighting(req: LightingSetupRequest):
    """Configure environment lighting."""
    logger.info("Setting up lighting: %d lights", len(req.lights))
    lights_code = ""
    for i, light_data in enumerate(req.lights):
        light_type = light_data.get("type", "directional")
        name = light_data.get("name", f"Light_{i}")
        position = light_data.get("position", [0, 3, 0])
        rotation = light_data.get("rotation", [-45, 0, 0])
        energy = light_data.get("energy", 2.0)
        color = light_data.get("color", [1.0, 1.0, 1.0])

        light_classes = {
            "directional": "DirectionalLight3D",
            "omni": "OmniLight3D",
            "spot": "SpotLight3D",
        }
        light_class = light_classes.get(light_type, "DirectionalLight3D")

        lights_code += f"""
    var light_{i} = {light_class}.new()
    light_{i}.name = "{name}"
    light_{i}.position = Vector3({position[0]}, {position[1]}, {position[2]})
    light_{i}.rotation_degrees = Vector3({rotation[0]}, {rotation[1]}, {rotation[2]})
    light_{i}.light_energy = {energy}
    light_{i}.light_color = Color({color[0]}, {color[1]}, {color[2]})
    scene.add_child(light_{i})
"""

    script = f"""
extends SceneTree

func _init():
    var scene = load("res://current_scene.tscn").instantiate()
{lights_code}
    var env = Environment.new()
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_energy = {req.ambient_light_energy}
    env.glow_enabled = {str(req.use_glow).lower()}
    scene.environment = env
    var scene_packed = PackedScene.new()
    scene_packed.pack(scene)
    ResourceSaver.save("res://current_scene.tscn", scene_packed)
    print(json.dumps({{"status": "ok", "lights": {len(req.lights)}}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "lights": len(req.lights)}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ════════════════════════════════════════════════════════════════
#  Animation
# ════════════════════════════════════════════════════════════════

class AnimationKeyframe(BaseModel):
    frame: int
    position: list[float] | None = None
    rotation: list[float] | None = None
    scale: list[float] | None = None

class AnimationTrackRequest(BaseModel):
    target: str
    keyframes: list[AnimationKeyframe]
    duration: float = 2.0

@app.post("/animation/track")
async def add_animation_track(req: AnimationTrackRequest):
    """Add an animation track to a node."""
    logger.info("Adding animation track: %s (%d keyframes)", req.target, len(req.keyframes))
    tween_code = ""
    for i, kf in enumerate(req.keyframes):
        if kf.position:
            tween_code += f"""
    tween.tween_property(target, "position", Vector3({kf.position[0]}, {kf.position[1]}, {kf.position[2]}), {req.duration * (i + 1) / len(req.keyframes)})
"""
        if kf.rotation:
            tween_code += f"""
    tween.parallel().tween_property(target, "rotation_degrees", Vector3({kf.rotation[0]}, {kf.rotation[1]}, {kf.rotation[2]}), {req.duration * (i + 1) / len(req.keyframes)})
"""

    script = f"""
extends SceneTree

func _init():
    var scene = load("res://current_scene.tscn").instantiate()
    var target = scene.get_node("{req.target}")
    if target:
        var tween = create_tween()
{tween_code}
    print(json.dumps({{"status": "ok", "target": "{req.target}", "keyframes": {len(req.keyframes)}}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        return {"status": "ok", "target": req.target, "keyframes": len(req.keyframes)}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ════════════════════════════════════════════════════════════════
#  Render
# ════════════════════════════════════════════════════════════════

class RenderStartRequest(BaseModel):
    output: str
    scene: str = "current_scene"
    resolution: list[int] = [1920, 1080]
    format: str = "png"

@app.post("/render/start")
async def start_render(req: RenderStartRequest):
    """Start rendering via Godot."""
    global _render_status
    logger.info("Starting render: %s (%dx%d)", req.output, req.resolution[0], req.resolution[1])
    _render_status = {"status": "rendering", "progress": 0.0, "output": req.output}

    script = f"""
extends SceneTree

func _init():
    var scene = load("res://{req.scene}.tscn").instantiate()
    var viewport = Viewport.new()
    viewport.size = Vector2i({req.resolution[0]}, {req.resolution[1]})
    viewport.render_target_update_mode = Viewport.UPDATE_ALWAYS
    viewport.add_child(scene)
    await get_tree().process_frame
    await get_tree().process_frame
    var image = viewport.get_texture().get_image()
    image.save_png("{req.output}")
    print(json.dumps({{"status": "completed", "output": "{req.output}"}}))
    quit()
"""
    result = _run_godot_script(script)
    if result["success"]:
        _render_status = {"status": "completed", "progress": 100.0, "output": req.output}
        return {"status": "completed", "output": req.output}
    _render_status = {"status": "error", "progress": 0.0}
    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


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
#  Export
# ════════════════════════════════════════════════════════════════

class ExportRequest(BaseModel):
    preset: str = "web"  # web, desktop, android
    output_path: str = "build/index.html"

@app.post("/export")
async def export_project(req: ExportRequest):
    """Export the project."""
    logger.info("Exporting project: preset=%s", req.preset)
    cmd = [GODOT_EXE, "--headless", "--path", GODOT_PROJECT, "--export-release", req.preset, req.output_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return {"status": "ok", "preset": req.preset, "output": req.output_path}
        raise HTTPException(status_code=500, detail=result.stderr)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Export timed out")


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8081)
