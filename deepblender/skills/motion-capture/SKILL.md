---
name: motion-capture
description: Import BVH/FBX mocap, retargeting sur squelettes VRM, nettoyage, blendshapes.
---

# Motion Capture Integration

Import et retargeting de animations motion capture.

## Formats supportes

| Format | Usage | Import |
|--------|-------|--------|
| BVH    | Animation squelette | `bpy.ops.import_anim.bvh()` |
| FBX    | Animation + mesh | `bpy.ops.import_scene.fbx()` |
| GLB/glTF | Animation + mesh | `bpy.ops.import_scene.gltf()` |
| CMU AMC | Recherche academique | Parser custom |

## Import BVH dans Blender

```python
import bpy

def import_bvh(filepath: str, scale: float = 1.0) -> str:
    """Importe un fichier BVH et retourne le nom de l'armature."""
    bpy.ops.import_anim.bvh(
        filepath=filepath,
        use_scale=True,
        scale=scale,
        use_front_neg_y=True,
    )
    armature = bpy.context.active_object
    return armature.name
```

## Retargeting sur squelette VRM

```python
def retarget_bvh_to_vrm(
    bvh_armature: str,
    vrm_armature: str,
    bone_mapping: dict[str, str] | None = None,
):
    """Retargete une animation BVV sur un squelette VRM.
    
    Mapping par defaut (Mixamo -> VRM humanoid):
    """
    default_mapping = {
        "Hips": "mixamorig:Hips",
        "Spine": "mixamorig:Spine",
        "Spine1": "mixamorig:Spine1",
        "Spine2": "mixamorig:Spine2",
        "Neck": "mixamorig:Neck",
        "Head": "mixamorig:Head",
        "LeftShoulder": "mixamorig:LeftShoulder",
        "LeftArm": "mixamorig:LeftArm",
        "LeftForeArm": "mixamorig:LeftForeArm",
        "LeftHand": "mixamorig:LeftHand",
        "RightShoulder": "mixamorig:RightShoulder",
        "RightArm": "mixamorig:RightArm",
        "RightForeArm": "mixamorig:RightForeArm",
        "RightHand": "mixamorig:RightHand",
        "LeftUpLeg": "mixamorig:LeftUpLeg",
        "LeftLeg": "mixamorig:LeftLeg",
        "LeftFoot": "mixamorig:LeftFoot",
        "RightUpLeg": "mixamorig:RightUpLeg",
        "RightLeg": "mixamorig:RightLeg",
        "RightFoot": "mixamorig:RightFoot",
    }
    mapping = bone_mapping or default_mapping
    
    # Copier les keyframes de l'armature source vers la cible
    # (implementation depend du squelette exact)
    pass
```

## Nettoyage d'animation

```python
def clean_mocap_animation(armature_name: str):
    """Nettoie une animation mocap : lissage, elimination du bruit."""
    armature = bpy.data.objects[armature_name]
    
    for bone in armature.data.bones:
        if bone.name in armature.animation_data.action.fcurves:
            for fcurve in armature.animation_data.action.fcurves:
                if fcurve.data_path.startswith(f'pose.bones["{bone.name}"]'):
                    # Lissage gaussien
                    for keyframe_point in fcurve.keyframe_points:
                        pass  # Apply smoothing filter
```

## Blendshapes pour expressions faciales

```python
def setup_facial_blendshapes(character_name: str):
    """Configure les blendshapes VRM pour les expressions faciales."""
    character = bpy.data.objects[character_name]
    
    # Blendshapes VRM standard
    vrm_expressions = [
        "happy", "angry", "sad", "surprised",
        "relaxed", "neutral", "aa", "ih", "ou",
        "ee", "oh", "blink", "blink_left", "blink_right",
    ]
    
    mesh = character.data
    for expr in vrm_expressions:
        if expr not in mesh.shape_keys.key_blocks:
            shape_key = mesh.shape_keys.key_blocks.new(name=expr, from_mix=False)
            shape_key.value = 0.0
```

## Lip Sync (phoneme -> blendshape)

```python
PHONEME_TO_VRM = {
    "A": "aa",
    "E": "ee", 
    "I": "ih",
    "O": "oh",
    "U": "ou",
    "M": "oh",  # Fermeture levres
    "F": "ee",
    "S": "ih",
    "T": "ih",
}

def apply_lip_sync(character_name: str, phonemes: list[tuple[float, str]]):
    """Applique un lip sync a un personnage VRM.
    
    phonemes: liste de (timestamp_secondes, phoneme_code)
    """
    character = bpy.data.objects[character_name]
    mesh = character.data
    
    for time_sec, phoneme in phonemes:
        frame = int(time_sec * 24)  # 24 FPS
        vrm_key = PHONEME_TO_VRM.get(phoneme, "neutral")
        
        if vrm_key in mesh.shape_keys.key_blocks:
            key = mesh.shape_keys.key_blocks[vrm_key]
            key.value = 1.0
            key.keyframe_insert(data_path="value", frame=frame)
            
            # Revenir a neutre apres 0.1s
            key.value = 0.0
            key.keyframe_insert(data_path="value", frame=frame + 2)
```

## Sources de donnees mocap

| Source | Licence | Format | Qualite |
|--------|---------|--------|---------|
| Mixamo | Gratuit (Adobe) | FBX | Haute |
| CMU MoCap | Domaine public | ASF/AMC | Haute |
| RenderPeople | Commercial | FBX/GLB | Tres haute |
| Quaternius | CC0 | FBX/GLB | Moyenne |
| TurboSquid | Mixte | FBX/OBJ | Variable |

## Regles

- Toujours nettoyer les animations mocap (bruit, jitter)
- Retargeting AVANT export VRM
- Tester les blendshapes avant rendu final
- preferer les sources CC0 quand possible
- Limiter le nombre de bones pour les performances web
