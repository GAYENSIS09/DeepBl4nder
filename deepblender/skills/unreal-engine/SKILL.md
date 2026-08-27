---
name: unreal-engine
description: Scripting Unreal Engine 5 via Python, MRQ automation, level sequencing, material creation.
---

# Unreal Engine 5 Integration

Scripting UE5 pour le rendu cinematographique haute fidelite.

## Architecture

```
DeepBlender API  →  REST API  →  UE5 Server (Python plugin)
                                   ├── Level creation
                                   ├── Material setup
                                   ├── Lighting (Lumen)
                                   └── MRQ (Movie Render Queue)
```

## Connexion

```python
import requests

UE5_API = "http://localhost:8080"

def ue5_command(endpoint: str, payload: dict) -> dict:
    """Envoie une commande au serveur UE5."""
    resp = requests.post(f"{UE5_API}/{endpoint}", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
```

## Commandes Python dans UE5

### Creation de level

```python
# Via le serveur REST UE5
ue5_command("level/create", {
    "name": "CyberpunkAlley",
    "template": "empty",
    "world_settings": {
        "gravity": (0, 0, -980),
        "kill_z": -10000
    }
})
```

### Materials (Lumen)

```python
ue5_command("material/create", {
    "name": "M_WetPavement",
    "base_color": (0.15, 0.15, 0.18),
    "roughness": 0.2,
    "metallic": 0.0,
    "normal强度": 0.8,
    "lumen_enabled": True
})
```

### Eclairage

```python
ue5_command("lighting/setup", {
    "sky_light": {"intensity": 1.0, "sky_distance": 100000},
    "directional": {"intensity": 3.0, "angle": 45},
    "rect_lights": [
        {"position": (0, 0, 300), "intensity": 5000, "size": (100, 100)}
    ],
    "lumen_quality": "high"
})
```

### Movie Render Queue (MRQ)

```python
ue5_command("mrq/render", {
    "sequence": "Seq_Main",
    "output_path": "/render/output/",
    "resolution": [1920, 1080],
    "fps": 24,
    "format": "png",
    "anti_aliasing": {"temporal_aa": True, "samples": 8},
    "console_commands": ["r.Lumen.TraceMeshSDFs 1"]
})
```

## Nanite

```python
# Activer Nanite pour des assets haute densite
ue5_command("mesh/enable_nanite", {
    "mesh_path": "/Game/Characters/Hero",
    "fallback_relative_error": 1.0
})
```

## MetaHuman

```python
# Importer un MetaHuman
ue5_command("metahuman/import", {
    "preset": "young_female",
    "customize": {
        "hair_color": (0.2, 0.15, 0.1),
        "skin_tone": "medium",
        "outfit": "casual"
    }
})
```

## Quand utiliser UE5

| Cas                          | UE5 | Blender |
|------------------------------|-----|---------|
| Personnages realistes        | ✅  | ⚠️      |
| Environnements photorealistes| ✅  | ⚠️      |
| Effets speciaux complexes    | ✅  | ⚠️      |
| Scenes simples               | ❌  | ✅      |
| Assets stylises              | ❌  | ✅      |
| Pas de GPU                   | ❌  | ✅      |

## Limites

- GPU requis (pas de CPU rendering)
- Licence EULA gratuit (< $1M revenue)
- Plus lent que Blender pour les scenes simples
- Script Python UE5 = IPython dans l'editor (pas standalone)

## Fallback

Si UE5 n'est pas disponible, fallback sur Blender avec EEVEE pour un rendu rapide.
