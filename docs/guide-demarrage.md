# Guide de démarrage — DeepBl4nder Local-First

DeepBl4nder s'exécute **entièrement en local** sur votre machine. Pas d'API keys, pas de cloud, pas de base de données externe.

## Prérequis

| Composant | Version | Notes |
|-----------|---------|-------|
| Python | 3.12+ | |
| GPU NVIDIA | 8 GB VRAM minimum | Requis pour le LLM local |
| Docker | 24+ | Avec NVIDIA Container Toolkit |
| Blender | 4.1+ | Optionnel (pour runs locaux) |

---

## Installation

### Option A : Via Docker (Recommandé)

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Télécharger les modèles Qwen3 GGUF
python -m DeepBl4nder.llm.download --all

# Lancer LLM + Blender worker
docker compose up -d
```

### Option B : Développement local (sans Docker)

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Installer avec TUI
pip install -e ".[tui]"

# Télécharger modèles
python -m DeepBl4nder.llm.download --all

# Lancer TUI (démarre le serveur LLM en interne)
DeepBl4nder tui
```

---

## Modèles LLM Locaux

DeepBl4nder utilise **Qwen3** via `llama-cpp-python` (GGUF Q4_K_M) :

| Modèle | VRAM | Rôle |
|--------|------|------|
| Qwen3-1.5B | ~1.5 GB | Routing, classification, validation |
| Qwen3-4B | ~3 GB | Chat général, résumé, traduction |
| Qwen3-8B | ~5.5 GB | Génération de code, raisonnement complexe |

**Routage en cascade** : le système essaie d'abord le plus petit modèle capable, puis escalade si nécessaire.

```bash
# Télécharger tous les modèles
python -m DeepBl4nder.llm.download --all

# Lister disponibles
python -m DeepBl4nder.llm.download --list

# Télécharger un modèle spécifique
python -m DeepBl4nder.llm.download --model qwen3-8b
```

Les modèles sont stockés dans `./models/` (gitignored).

---

## Docker Compose

```bash
# Core : LLM server + Blender worker
docker compose up -d

# Profils optionnels
docker compose --profile ue5 up -d       # Unreal Engine 5
docker compose --profile godot up -d     # Godot 4
docker compose --profile ai-video up -d  # AI Video
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `llm-server` | 8080 | llama.cpp avec Qwen3 (GPU) |
| `blender-worker` | — | Blender 4.1 headless + FFmpeg |
| `ue5-server` | 8081 | Unreal Engine 5 (profile `ue5`) |
| `godot-server` | 8082 | Godot 4 (profile `godot`) |
| `ai-video-server` | 8083 | AI Video (profile `ai-video`) |

### GPU

Nécessite **NVIDIA Container Toolkit** :

```bash
# Vérifier accès GPU
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

---

## Lancer le TUI

```bash
# Si Docker tourne (connecte au serveur LLM sur port 8080)
DeepBl4nder tui

# Sans Docker (démarre le serveur LLM en interne)
DeepBl4nder tui
```

### Interface TUI

L'interface terminal inclut :

- **Console** : Brief input, engine picker, run/cancel
- **Agent Stream** : Flux live des raisonnements agents (style opencode)
- **Side Panel** : Budget, step courant, modèle LLM actif
- **Library** : Productions et artefacts avec preview
- **Settings** : Config pipeline, budget, chemins

### Raccourcis TUI

| Touche | Action |
|--------|--------|
| `Ctrl+Q` | Quitter |
| `Ctrl+B` | Ouvrir Library |
| `Ctrl+O` | Settings |
| `F1` | Aide |

---

## Pipeline de Production

```
Brief → Story → Storyboard → Director → Character/Environment → Blender → QA → Render
```

### Étapes

| Étape | Agent | Description |
|-------|-------|-------------|
| 1 | **Story** | Structure narrative, actes, beats, dialogues |
| 2 | **Storyboard** | Plan visuel, caméras, composition |
| 3 | **Director** | Décisions finales, coordination |
| 4 | **Character/Env** | Design personnages, environnements |
| 5 | **Blender** | Génération script bpy, exécution |
| 6 | **QA** | Validation qualité, score, issues |
| 7 | **Render** | Rendu final (Cycles/EEVEE) |
| 8 | **Post-prod** | Audio, compositing, review, localisation |

### Boucle de révision

Si QA échoue → feedback → révision automatique → re-QA (max 3 itérations par défaut).

---

## Commandes CLI

```bash
# Inspecter l'environnement
DeepBl4nder inspect

# Valider un script Blender
DeepBl4nder validate script.py

# Télécharger modèles
DeepBl4nder download --all

# Lancer TUI
DeepBl4nder tui
```

---

## Structure des Données

Les productions sont stockées localement dans `data/runs/{production_id}/` :

```
data/runs/{id}/
├── events.jsonl      # Journal d'événements (NDJSON)
├── brief.json        # Brief original
├── artifacts/        # Artefacts générés
└── qa_report.json    # Rapport QA final
```

---

## Dépannage

| Problème | Solution |
|----------|----------|
| `docker compose up` échoue GPU | Installer NVIDIA Container Toolkit |
| Modèles non trouvés | `python -m DeepBl4nder.llm.download --all` |
| TUI ne se connecte pas au LLM | Vérifier `docker compose ps` et port 8080 |
| Blender non trouvé | Définir `BLENDER_EXE` ou installer Blender 4.1+ |
| VRAM insuffisante | Utiliser modèle plus petit (1.5B) |

---

## Variables d'Environnement

```bash
# Modèles
DeepBl4nder_MODELS_DIR=./models

# LLM
DeepBl4nder_LLM_HOST=127.0.0.1
DeepBl4nder_LLM_PORT=8080

# Blender
BLENDER_EXE=/usr/local/bin/blender

# Budget
DeepBl4nder_BUDGET=1.0
```