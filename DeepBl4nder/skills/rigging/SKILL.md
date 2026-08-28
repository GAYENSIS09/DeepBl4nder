---
name: rigging
description: Créer et valider les rigs : armatures, poids, contraintes, contrôleurs.
---

# Rigging

Rigger personnages et objets pour une animation prévisible. Le rig est l'interface entre le modèle et l'animation.

## Principes fondamentaux

- **Hiérarchie propre** : chaque bone a un parent clair.
- **Poids propres** : max 4 influences par vertex.
- **Contrôleurs simples** : moins de contraintes = plus prévisible.
- **Déterminisme** : la pose par défaut doit être stable.

## Armature de base (personnage)

```python
import bpy

# Créer l'armature
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
armature = bpy.context.active_object
armature.name = "Armature_Character"
bone = armature.data.edit_bones[0]
bone.name = "root"

# Spine
bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={"value": (0, 0, 1)})
spine = bpy.context.active_object.data.edit_bones.active
spine.name = "spine"

bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={"value": (0, 0, 1)})
chest = bpy.context.active_object.data.edit_bones.active
chest.name = "chest"

bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={"value": (0, 0, 0.5)})
head = bpy.context.active_object.data.edit_bones.active
head.name = "head"

# Bras ( partir du chest)
bpy.context.active_object.data.edit_bones.active = chest
bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={"value": (1, 0, 0.5)})
shoulder = bpy.context.active_object.data.edit_bones.active
shoulder.name = "shoulder_L"

bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={"value": (1, 0, 0)})
upper_arm = bpy.context.active_object.data.edit_bones.active
upper_arm.name = "upper_arm_L"

bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={"value": (0.8, 0, 0)})
forearm = bpy.context.active_object.data.edit_bones.active
forearm.name = "forearm_L"

bpy.ops.armature.extrude_move(TRANSFORM_OT_translate={"value": (0.3, 0, 0)})
hand = bpy.context.active_object.data.edit_bones.active
hand.name = "hand_L"

bpy.ops.object.mode_set(mode='OBJECT')
```

## Hiérarchie standard

```
root
├── spine
│   ├── chest
│   │   ├── head
│   │   ├── shoulder_L
│   │   │   └── upper_arm_L
│   │   │       └── forearm_L
│   │   │           └── hand_L
│   │   └── shoulder_R
│   │       └── upper_arm_R
│   │           └── forearm_R
│   │               └── hand_R
├── hip_L
│   └── upper_leg_L
│       └── lower_leg_L
│           └── foot_L
└── hip_R
    └── upper_leg_R
        └── lower_leg_R
            └── foot_R
```

## Weight Painting

```python
# Passer en mode Weight Paint
bpy.ops.object.mode_set(mode='WEIGHT_PEAINT')

# Sélectionner un bone
bpy.context.active_object.data.bones.active = bpy.context.active_object.data.bones["upper_arm_L"]

# Peindre les poids
# 1.0 = influencé à 100%
# 0.0 = pas influencé
# Valeurs intermédiaires = influencé partiellement
```

### Règles de poids
- **Max 4 influences par vertex** : au-delà, artefacts.
- **Pas de poids > 1.0** : cause des déformations extrêmes.
- **Pas de poids < 0.0** : peut causer des erreurs.
- **Automatique d'abord** : `bpy.ops.object.vertex_group_limit_total(group_select_mode='BONE')`

## Contraintes courantes

### IK (Inverse Kinematics)
```python
# Contrainte IK sur le bras
bpy.ops.object.mode_set(mode='POSE')

# Sélectionner le forearm
bone = armature.pose.bones["forearm_L"]

# Ajouter contrainte IK
constraint = bone.constraints.new(type='IK')
constraint.target = bpy.data.objects["Armature_Character"]
constraint.subtarget = "hand_IK_L"  # bone contrôleur
constraint.chain_count = 2  # upper_arm + forearm
```

### Track To
```python
# La tête suit la cible
constraint = armature.pose.bones["head"].constraints.new(type='TRACK_TO')
constraint.target = bpy.data.objects["head_target"]
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'
```

### Copy Rotation
```python
# Le chest copie la rotation du spine
constraint = armature.pose.bones["chest"].constraints.new(type='COPY_ROTATION')
constraint.target = bpy.data.objects["Armature_Character"]
constraint.subtarget = "spine"
constraint.target_space = 'LOCAL'
constraint.owner_space = 'LOCAL'
```

## Pose Library

```python
# Créer une pose library
bpy.ops.poselib.new(name="PoseLibrary")

# Enregistrer une pose
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.poselib.add_pose(name="neutral")

# Appliquer une pose
bpy.ops.poselib.apply_pose(pose_name="neutral")
```

## Validation

```python
# Vérifier l'armature
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.armature.select_all(action='SELECT')

# Vérifier les poids
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
# Utiliser l'outil "Weight Gradient" pour vérifier visuellement

# Vérifier la pose par défaut
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.transforms_clear()
```

## Erreurs courantes

1. **Hiérarchie cassée** : bones sans parent = déformation imprévisible.
2. **Poids > 4 influences** : artefacts de déformation.
3. **Pose par défaut instable** : bones qui se croisent, déformations bizarres.
4. **Contraintes trop complexes** : comportement imprévisible.
5. **Pas de test** : ne pas vérifier chaque bone en pose = surprises.

## Règles

- Chaîne propre : armature → bones avec hiérarchie lisible (hips, spine, chest, head…).
- Weight painting : éviter les influences croisées excessives (max ~4 groupes/os).
- Ajouter des contrôleurs (IK/FK) uniquement quand le besoin est explicite.
- Valider : pose par défaut stable, aucune déformation cassée, scale de bone correcte.
- Livrer un `RigSpec` + `WeightReport` et une `PoseLibrary` de base.
- Enregistrer le rig comme asset versionné avec son poids (weight painting) vérifié.
