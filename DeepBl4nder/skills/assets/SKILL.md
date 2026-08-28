---
name: assets
description: Gérer le cycle de vie des assets : recherche, génération, import, validation, versioning.
---

# Assets

Ordonner l'acquisition et la gestion des assets d'une production. Un asset est toute ressource utilisée dans la production.

## Cycle de vie

```
Search → Generate → Import → Validate → Register → Version
```

### 1. Search (Recherche)
- Chercher dans la bibliothèque existante.
- Vérifier les dépendances et la licence.
- Estimer le temps de modification si nécessaire.

### 2. Generate (Génération)
- Créer l'asset via Blender (modeling, texturing, etc.).
- Utiliser des primitives et des opérations déterministes.
- Suivre les conventions de nommage.

### 3. Import (Import)
```python
import bpy

# Importer un OBJ
bpy.ops.import_scene.obj(filepath="//assets/prop_table.obj")

# Importer un FBX
bpy.ops.import_scene.fbx(filepath="//assets/character.fbx")

# Importer un glTF
bpy.ops.import_scene.gltf(filepath="//assets/environment.glb")

# Importer une image comme texture
img = bpy.data.images.load("//textures/diffuse.png")
```

### 4. Validate (Validation)
- **Géométrie** : pas de normals inversées, pas de vertices doubles.
- **Scale** : appliquée, échelle réaliste.
- **UV** : dépliées, pas de chevauchement.
- **Matériaux** : assignés, PBR valides.
- **Rig** : fonctionnel, poids valides.
- **Polycount** : dans le budget.

```python
# Validation rapide
import bpy

obj = bpy.context.active_object

# Vérifier les normals
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

# Vérifier les vertices doubles
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.object.mode_set(mode='OBJECT')

# Appliquer la scale
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
```

### 5. Register (Enregistrement)
```python
# Enregistrer dans le registry
asset_info = {
    "name": "prop_table",
    "type": "prop",
    "version": "1.0",
    "hash": "abc123",  # hash du fichier
    "path": "//assets/prop_table.blend",
    "dependencies": [],
    "polycount": 2048,
    "materials": ["wood_oak", "metal_iron"],
    "created": "2025-01-15",
    "author": "BlenderAgent"
}
```

### 6. Version (Versionnage)
```
assets/
├── prop_table/
│   ├── prop_table_v1.blend
│   ├── prop_table_v2.blend
│   └── prop_table_v3.blend
```

- **Version majeure** : changement de forme, de scale, de拓扑.
- **Version mineure** : correction de matériaux, d'UV.
- **Ne jamais écraser** une version publiée.

## Conventions de nommage

```
<type>_<name>_<variant>

Types : char (character), prop, env (environment), mat (material), tex (texture)
Variantes : _large, _small, _red, _damaged, etc.

Exemples :
char_hero_red
prop_table_oak
env_forest_autumn
mat_metal_iron
tex_wood_diffuse
```

## Budget par type d'asset

| Type | Polycount max | Texture résolution | Matériaux |
|------|--------------|-------------------|-----------|
| Prop simple | 2K-5K | 1024 | 1-2 |
| Prop détaillé | 5K-20K | 2048 | 2-4 |
| Personnage | 10K-50K | 4096 | 3-6 |
| Environnement | 20K-100K | 2048-4096 | 5-10 |

## Patterns courants

### Asset procedural (généré par code)
```python
import bpy

# Générer un prop simple
bpy.ops.mesh.primitive_cube_add(size=1)
obj = bpy.context.active_object
obj.name = "prop_box"

# Ajouter un matériau
mat = bpy.data.materials.new(name="mat_cardboard")
mat.use_nodes = True
obj.data.materials.append(mat)

# Appliquer la scale
bpy.ops.object.transform_apply(scale=True)
```

### Asset importé et nettoyé
```python
import bpy

# Importer
bpy.ops.import_scene.obj(filepath="//assets/raw_prop.obj")
imported = bpy.context.selected_objects[0]

# Nettoyer
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.object.mode_set(mode='OBJECT')

# Appliquer la scale
bpy.ops.object.transform_apply(scale=True)

# Renommer
imported.name = "prop_cleaned"
```

## Erreurs courantes

1. **Pas de versionnage** : impossible de revenir en arrière.
2. **Écraser un asset** : perte de travail.
3. **Pas de validation** : asset cassé dans la scène.
4. **Mauvais nommage** : confusion dans les projets complexes.
5. **Oublier les dépendances** : asset qui référence des fichiers manquants.
6. **Scale non appliquée** : collisions incorrectes, textures étirées.

## Règles

- Pipeline : Search / Generate / Import → Validate → Register → Version.
- Conventions de nommage stables (`<type>_<name>_<version>`).
- Valider chaque asset : polycount, scale, textures référencées, rig fonctionnel.
- Enregistrer dans le registry avec hash, provenance et dépendances.
- Versionner à chaque modification ; ne jamais écraser un asset publié.
- Types couverts : characters, props, environment, textures, HDRI, audio.
