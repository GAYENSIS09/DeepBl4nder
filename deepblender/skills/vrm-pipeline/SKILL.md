---
name: vrm-pipeline
description: Création, import, export de modèles VRM pour avatars cross-platform.
---

# VRM Pipeline

Format standard pour avatars 3D cross-platform (VR, AR, jeux, animation).

## Qu'est-ce que VRM ?

VRM est un format basé sur glTF 2.0 pour les avatars 3D. Il standardise :
- La géométrie du personnage
- Le squelette (armature)
- Les morph targets (expressions faciales)
- Les matériaux (MToon pour le style anime)
- Les métadonnées (nom, description, licence)

## Extensions VRM

| Extension     | Version | Usage                          |
|---------------|---------|--------------------------------|
| VRM 0.x       | 0.x     | Legacy, encore courant         |
| VRM 1.0       | 1.0     | Standard actuel, recommandé    |
| VRMA          | 1.0     | Animations cross-platform      |
| VRM CF        | 1.0     | Custom fields (métadonnées)    |

## Import dans Blender

### Via le module bpy
```python
import bpy

# Import glTF/VRM (Blender 4.0+)
bpy.ops.import_scene.gltf(
    filepath="//assets/character.vrm",
    import_cameras=False,
    import_lights=False,
)

# Le mesh et l'armature sont importés automatiquement
# Les morph targets (expressions) sont préservés
```

### Vérification après import
```python
# Lister les morph targets
obj = bpy.data.objects["Avatar"]
if obj.data.shape_keys:
    for key in obj.data.shape_keys.key_blocks:
        print(f"Morph: {key.name} (value: {key.value})")

# Vérifier l'armature
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        print(f"Armature: {obj.name}")
        for bone in obj.data.bones:
            print(f"  Bone: {bone.name}")
```

## Export vers VRM

### Prérequis
- Installer l'add-on VRM (blender-vrm)
- Ou utiliser le script Python directement

### Export basique
```python
import bpy

# Sélectionner le mesh et l'armature
bpy.ops.export_scene.vrm(
    filepath="//output/avatar.vrm",
    export_selected=True,
)
```

## Morph Targets (VRM Expressions)

### Visimes (phonèmes pour lip sync)
```python
# VRM définit ces visimes standard
VISIMES = {
    "aa": "A",    # Bouche ouverte
    "ih": "I",    # Bouche étirée
    "ou": "U",    # Bouche arrondie
    "ee": "E",    # Bouche étirée horizontalement
    "oh": "O",    # Bouche ronde
}

# Animation du lip sync
for frame, viseme in enumerate(voice_track.visemes):
    for morph_name, value in viseme.items():
        key = obj.data.shape_keys.key_blocks[morph_name]
        key.value = value
        key.keyframe_insert(data_path="value", frame=frame)
```

### Expressions faciales (VRM 1.0)
```python
# VRM 1.0 définit ces groupes d'expressions
EXPRESSION_GROUPS = {
    "happy": ["happy", "happyLeft", "happyRight"],
    "sad": ["sad", "sadLeft", "sadRight"],
    "angry": ["angry", "angryLeft", "angryRight"],
    "surprised": ["surprised"],
    "blink": ["blink", "blinkLeft", "blinkRight"],
    "neutral": ["neutral"],
}

# Exemple : animation triste
key = obj.data.shape_keys.key_blocks["sad"]
key.value = 0.8
key.keyframe_insert(data_path="value", frame=10)
```

## Animation avec VRM (VRMA)

### Clips d'animation
```python
# Structure d'un clip VRMA
clip = {
    "name": "Walk Cycle",
    "duration": 1.0,  # secondes
    "fps": 30,
    "humanoidTracks": {
        "spine": {
            "rotation": [
                {"frame": 0, "value": [0, 0, 0, 1]},
                {"frame": 15, "value": [0, 0, 0.1, 0.99]},
                {"frame": 30, "value": [0, 0, 0, 1]},
            ]
        },
        "leftUpperArm": {
            "rotation": [
                {"frame": 0, "value": [0, 0, 0, 1]},
                {"frame": 15, "value": [0, 0, -0.3, 0.95]},
                {"frame": 30, "value": [0, 0, 0, 1]},
            ]
        },
    },
    "expressionTracks": {
        "happy": [
            {"frame": 0, "value": 0.0},
            {"frame": 15, "value": 0.5},
            {"frame": 30, "value": 0.0},
        ]
    }
}
```

## Intégration avec DeepBlender

### CharacterDesigner → VRM
```python
# Le CharacterDesigner génère un CharacterModel
# avec import_path pointant vers un fichier VRM

character = CharacterModel(
    name="Hero",
    description="Main character, anime style",
    geometry_type="vrm",
    import_path="assets/characters/hero.vrm",
    skeleton_type="humanoid",
    blendshapes=["happy", "sad", "angry", "blink", "aa", "ou"],
)
```

### AnimatorAgent → VRMA
```python
# L'AnimatorAgent génère des AnimationClips
# qui peuvent être exportés en VRMA

clip = AnimationClip(
    character_name="Hero",
    shot_index=0,
    keyframes=[
        Keyframe(frame=0, property_path="location", value=[0, 0, 0]),
        Keyframe(frame=24, property_path="location", value=[2, 0, 0]),
    ],
    lip_sync=True,
    expression="angry",
    duration=1.0,
    fps=24,
)
```

## Règles

- Utiliser VRM 1.0 pour les nouveaux projets
- Toujours inclure les morph targets de base (blink, lip sync)
- Tester les expressions avant l'animation
- Garder l'armature compatible humanoid VRM
- Exporter les animations séparément (VRMA)
- Documenter la licence du modèle
