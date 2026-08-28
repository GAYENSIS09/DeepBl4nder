---
name: polyhaven
description: Intégration Poly Haven API : HDRIs, textures, modèles 3D CC0 pour scènes Blender.
---

# Poly Haven Integration

Accéder aux assets CC0 de Poly Haven (HDRIs, textures, modèles 3D) pour enrichir les scènes Blender.

## API Poly Haven

Base URL: `https://api.polyhaven.com`

### Endpoints principaux

| Endpoint             | Description                        | Exemple                              |
|---------------------|------------------------------------|--------------------------------------|
| `/assets`           | Lister les assets (filtrable)     | `GET /assets?t=hdris&c=outdoor`      |
| `/asset/{name}`     | Métadonnées d'un asset            | `GET /asset/studio_small_09`         |
| `/files/{name}`     | Fichiers disponibles              | `GET /files/studio_small_09`         |
| `/categories`       | Catégories disponibles            | `GET /categories`                    |
| `/tags`             | Tags disponibles                  | `GET /tags`                          |

### Types d'assets

| Type      | Format           | Usage                              |
|-----------|-----------------|------------------------------------|
| `hdris`   | .exr (16-bit)   | Éclairage réaliste (IBL)           |
| `textures`| .png/.exr       | PBR materials (albedo, normal...)  |
| `models`  | .fbx/.glb/.blend| Modèles 3D prêts à l'emploi        |

## Usage dans Blender

### Télécharger et appliquer un HDRI
```python
import bpy
import requests
import os

def download_hdri(name: str, output_dir: str) -> str:
    """Télécharge un HDRI depuis Poly Haven."""
    # Obtenir les fichiers
    resp = requests.get(f"https://api.polyhaven.com/files/{name}")
    resp.raise_for_status()
    files = resp.json()

    # Télécharger la version 1k (ou 2k pour meilleure qualité)
    exr_url = files.get("hdri", {}).get("1k", {}).get("exr")
    if not exr_url:
        exr_url = files.get("hdri", {}).get("2k", {}).get("exr")

    # Télécharger
    hdri_path = os.path.join(output_dir, f"{name}.exr")
    with requests.get(exr_url, stream=True) as r:
        r.raise_for_status()
        with open(hdri_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return hdri_path

def apply_hdri(name: str, output_dir: str) -> None:
    """Applique un HDRI comme éclairage de scène."""
    hdri_path = download_hdri(name, output_dir)

    # Configurer le world
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()

    # Environment Texture
    env_tex = nodes.new("ShaderNodeTexEnvironment")
    env_tex.image = bpy.data.images.load(hdri_path)

    # Mapping pour rotation
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0, 0, 0)

    # Texture Coordinate
    tex_coord = nodes.new("ShaderNodeTexCoord")

    # Output
    output = nodes.new("ShaderNodeOutputWorld")

    # Connect
    world.node_tree.links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    world.node_tree.links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
    world.node_tree.links.new(env_tex.outputs["Color"], output.inputs["Surface"])
```

### Télécharger et appliquer une texture PBR
```python
def download_texture(name: str, output_dir: str) -> dict[str, str]:
    """Télécharge les maps PBR d'une texture."""
    resp = requests.get(f"https://api.polyhaven.com/files/{name}")
    resp.raise_for_status()
    files = resp.json()

    maps = {}
    tex_files = files.get("texture", {})
    for map_type, resolutions in tex_files.items():
        # Prendre la résolution la plus basse pour commencer
        for res in ["1k", "2k", "4k"]:
            if res in resolutions:
                url = resolutions[res]
                ext = url.rsplit(".", 1)[-1]
                filepath = os.path.join(output_dir, f"{name}_{map_type}.{ext}")
                with requests.get(url, stream=True) as r:
                    r.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                maps[map_type] = filepath
                break
    return maps

def apply_texture(obj, name: str, output_dir: str) -> None:
    """Applique une texture PBR à un objet."""
    maps = download_texture(name, output_dir)

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    if "diffuse" in maps:
        img = bpy.data.images.load(maps["diffuse"])
        bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        mat.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    if "normal" in maps:
        img = bpy.data.images.load(maps["normal"])
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        tex_node.image.colorspace_settings.name = "Non-Color"
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = 1.0
        mat.node_tree.links.new(tex_node.outputs["Color"], normal_map.inputs["Color"])
        mat.node_tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

    if "roughness" in maps:
        img = bpy.data.images.load(maps["roughness"])
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        tex_node.image.colorspace_settings.name = "Non-Color"
        mat.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Roughness"])

    obj.data.materials.append(mat)
```

### Télécharger un modèle 3D
```python
def download_model(name: str, output_dir: str) -> str:
    """Télécharge un modèle 3D depuis Poly Haven."""
    resp = requests.get(f"https://api.polyhaven.com/files/{name}")
    resp.raise_for_status()
    files = resp.json()

    model_files = files.get("fbx", files.get("glb", {}))
    for fmt in ["fbx", "glb"]:
        if fmt in files:
            model_files = files[fmt]
            break

    # Prendre la meilleure qualité disponible
    url = None
    for res in ["1k", "2k", "4k"]:
        if res in model_files:
            url = model_files[res]
            break

    if not url:
        raise ValueError(f"No model files found for {name}")

    ext = url.rsplit(".", 1)[-1]
    filepath = os.path.join(output_dir, f"{name}.{ext}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return filepath
```

## Recherche d'assets

```python
def search_polyhaven(category: str = "hdris", tags: list[str] | None = None, limit: int = 10) -> list[dict]:
    """Recherche des assets sur Poly Haven."""
    params = {"t": category, "limit": limit}
    if tags:
        params["c"] = ",".join(tags)

    resp = requests.get("https://api.polyhaven.com/assets", params=params)
    resp.raise_for_status()
    assets = resp.json()

    return [
        {
            "name": name,
            "category": category,
            "tags": info.get("tags", []),
            "date_published": info.get("date_published"),
        }
        for name, info in list(assets.items())[:limit]
    ]

# Exemples de recherche
outdoor_hdris = search_polyhaven("hdris", tags=["outdoor", "nature"], limit=5)
brick_textures = search_polyhaven("textures", tags=["brick", "wall"], limit=5)
tree_models = search_polyhaven("models", tags=["tree", "plant"], limit=5)
```

## Intégration avec DeepBl4nder

### DirectorAgent → Asset Search
```python
# Le DirectorAgent identifie les besoins en assets
# et cherche sur Poly Haven

assets_needed = {
    "hdri": "studio_small_09",  # Éclairage studio
    "texture": "brick_01",       # Texture mur
    "model": "tree_01",          # Arbre
}

# Téléchargement automatique
for asset_type, name in assets_needed.items():
    if asset_type == "hdri":
        apply_hdri(name, "//assets/hdris/")
    elif asset_type == "texture":
        # Appliquer à tous les objets de la scène
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                apply_texture(obj, name, "//assets/textures/")
    elif asset_type == "model":
        path = download_model(name, "//assets/models/")
        bpy.ops.import_scene.gltf(filepath=path)
```

## Règles

- Toujours utiliser CC0 (public domain) pour les assets Poly Haven
- Préférer les résolutions basses (1k) pour le dev, hautes pour le rendu final
- Cacheer les téléchargements pour éviter les appels API redondants
- Documenter les sources d'assets dans les métadonnées de production
- Vérifier la licence avant tout usage commercial
