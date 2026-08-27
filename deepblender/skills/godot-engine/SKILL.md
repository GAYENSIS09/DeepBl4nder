---
name: godot-engine
description: GDScript, scenes, signaux, physically-based rendering, export WebGL via Godot 4 headless.
---

# Godot 4 Engine Integration

Moteur leger pour scenes web-ready et prototypage rapide.

## Architecture

```
DeepBl4nder API  →  REST API  →  Godot Headless (GDScript)
                                  ├── Scene creation
                                  ├── PBR materials
                                  ├── Animation
                                  └── Export (WebGL, desktop)
```

## Commande Godot Headless

```bash
# Executer un script GDScript
godot --headless --script res://scene_builder.gd

# Exporter un projet
godot --headless --export-release "Web" build/index.html
```

## GDScript — Structure de scene

```gdscript
# scene_builder.gd
extends SceneTree

func _init():
    # Creer la scene
    var root = Node3D.new()
    root.name = "MainScene"
    
    # Sol
    var ground = MeshInstance3D.new()
    ground.mesh = PlaneMesh.new()
    ground.mesh.size = Vector2(40, 40)
    var ground_mat = StandardMaterial3D.new()
    ground_mat.albedo_color = Color(0.2, 0.2, 0.25)
    ground.material_override = ground_mat
    root.add_child(ground)
    
    # Camera
    var camera = Camera3D.new()
    camera.position = Vector3(0, 3, 8)
    camera.look_at(Vector3(0, 1, 0))
    root.add_child(camera)
    
    # Eclairage
    var light = DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-45, 0, 0)
    light.light_energy = 2.0
    root.add_child(light)
    
    # Sauvegarder la scene
    var scene_packed = PackedScene.new()
    scene_packed.pack(root)
    ResourceSaver.save("res://main_scene.tscn", scene_packed)
```

## PBR Materials (StandardMaterial3D)

```gdscript
func create_material(base_color: Color, roughness: float, metallic: float) -> StandardMaterial3D:
    var mat = StandardMaterial3D.new()
    mat.albedo_color = base_color
    mat.roughness = roughness
    mat.metallic = metallic
    mat.metallic_specular = 0.5
    # Emissive
    mat.emission_enabled = false
    # Transparency
    mat.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
    return mat
```

## Animation

```gdscript
func animate_camera(camera: Camera3D, duration: float):
    var tween = create_tween()
    tween.tween_property(camera, "position", Vector3(5, 3, 5), duration)
    tween.parallel().tween_property(camera, "rotation_degrees", Vector3(-30, 45, 0), duration)
```

## Signaux (evenements)

```gdscript
# Connecter des signaux pour l'orchestration
signal scene_ready
signal animation_complete

func _ready():
    emit_signal("scene_ready")

func _on_animation_complete():
    emit_signal("animation_complete")
```

## Export WebGL

```bash
# Exporter pour le web
godot --headless --export-release "Web" build/index.html

# Assets necessaires
# - export_presets.cfg avec preset "Web"
# - build/index.html (template)
```

## Quand utiliser Godot

| Cas                          | Godot | Blender |
|------------------------------|-------|---------|
| Prototype rapide             | ✅    | ⚠️      |
| Scene web (WebGL)            | ✅    | ❌      |
| Assets legers                | ✅    | ⚠️      |
| Qualite cinematographique    | ❌    | ✅      |
| Personnages detailles        | ❌    | ✅      |
| Calcul lourd (physique)      | ⚠️    | ✅      |

## Limites

- Pas de rendu offline haute qualite
- Moins de fonctionnalites 3D que Blender/UE5
- GDScript = syntaxe differente de Python
- Export WebGL = contraintes de taille/assets

## Fallback

Si Godot n'est pas disponible, fallback sur Blender pour tout type de scene.
