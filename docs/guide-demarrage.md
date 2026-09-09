# Guide de démarrage — DeepBl4nder

DeepBl4nder est un système de production audiovisuelle multi-agents. Il utilise un **routeur LLM cloud multi-fournisseurs** (via `litellm`) et Blender 4.1+ pour le rendu 3D. **Au moins une clé API LLM est requise**.

## Prérequis

| Composant | Version | Notes |
|-----------|---------|-------|
| Python | 3.12+ | |
| Blender | 4.1+ | Requis — moteur de rendu 3D unique (Cycles/EEVEE) |
| Docker | 24+ | Optionnel (recommandé) |

### Clés API (au moins une requise)

| Fournisseur | Variable d'environnement |
|-------------|--------------------------|
| Gemini | `GEMINI_API_KEY` |
| Groq | `GROQ_API_KEY` |
| NVIDIA | `NVIDIA_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Cloudflare | `CLOUDFLARE_API_KEY` + `CLOUDFLARE_ACCOUNT_ID` |

---

## Installation

### Option A : Via Docker (Recommandé)

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Configurer les clés API (au moins une)
cp .env.example .env
# Éditer .env avec vos clés API

# Lancer Blender worker + pipeline
docker compose up -d
```

### Option B : Développement local (sans Docker)

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Installer avec TUI
pip install -e ".[tui]"

# Configurer les clés API
cp .env.example .env
# Éditer .env avec vos clés API

# Lancer TUI
DeepBl4nder tui
```

---

## Routeur LLM Multi-Fournisseurs

DeepBl4nder utilise `litellm` via un routeur cloud centralisé (`DeepBl4nder/llm/`). Les 5 fournisseurs supportés :

| Fournisseur | Modèle par défaut | Variable d'environnement |
|-------------|-------------------|--------------------------|
| Google Gemini | `gemini/gemini-3.6-flash` | `GEMINI_API_KEY` |
| Groq | `groq/openai/gpt-oss-120b` | `GROQ_API_KEY` |
| NVIDIA NIM | `nvidia_nim/meta/llama-3.3-70b-instruct` | `NVIDIA_API_KEY` |
| OpenRouter | `openrouter/meta-llama/llama-3.3-70b-instruct` | `OPENROUTER_API_KEY` |
| Cloudflare Workers AI | `cloudflare/@cf/meta/llama-3.3-70b-instruct` | `CLOUDFLARE_API_KEY` |

**Modes de routage** (configurables via `DeepBl4nder_LLM_MODE`) :
- **fallback** (défaut) : un seul fournisseur sollicité par appel, basculement sur erreur.
- **vote** : tous les fournisseurs sains votent, majorité gagne.

Le routeur implémente l'interface `UnifiedLLM` de NOOA, avec découverte dynamique des modèles via l'endpoint `/models` de chaque fournisseur, protection cooldown par provider, et budget USD configurable.

---

## Docker Compose

```bash
# Core : Blender worker
docker compose up -d

# TUI
docker compose --profile tui up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `blender-worker` | — | Blender 4.1 headless + FFmpeg |

---

## Lancer le TUI

```bash
# Lancer TUI
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
| 3 | **Director** | Décisions finales, SceneSpec |
| 4 | **Character/Env** | Design personnages, environnements |
| 5 | **Blender** | Génération script bpy, exécution |
| 6 | **QA** | Validation qualité, score, issues |
| 7 | **Render** | Rendu final (Cycles/EEVEE) |
| 8 | **Post-prod** | Audio, compositing, review, localisation |

### Boucle de révision

Si QA échoue → feedback → révision automatique → re-QA (max 3 itérations par défaut). Sinon le run passe en `blocked`.

---

## Commandes CLI

```bash
# Inspecter l'environnement
DeepBl4nder inspect

# Valider un script Blender
DeepBl4nder validate script.py

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
| `Aucune clé API LLM` | Configurer au moins une variable d'environnement (`GEMINI_API_KEY`, etc.) dans `.env` |
| TUI ne se connecte pas au LLM | Vérifier les variables d'environnement dans `.env` |
| Blender non trouvé | Définir `BLENDER_EXE` ou installer Blender 4.1+ |

---

## Variables d'Environnement

```bash
# LLM (au moins une requise)
GEMINI_API_KEY=...
GROQ_API_KEY=...
NVIDIA_API_KEY=...
OPENROUTER_API_KEY=...
CLOUDFLARE_API_KEY=...
CLOUDFLARE_ACCOUNT_ID=...

# Mode de routage LLM (fallback ou vote)
DeepBl4nder_LLM_MODE=fallback

# Budget max par production
DeepBl4nder_BUDGET=1.0

# Blender
BLENDER_EXE=/usr/local/bin/blender
```
