# DeepBl4nder — Documentation Référence du Projet

> Version : **0.2.0** | Python >= 3.12 | Licence interne
>
> Dernière mise à jour : 2026-08-27

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture technique](#2-architecture-technique)
3. [Installation et déploiement](#3-installation-et-déploiement)
4. [Pipeline de production](#4-pipeline-de-production)
5. [Base de données](#5-base-de-données)
6. [Tests](#6-tests)
7. [Scripts de déploiement](#7-scripts-de-déploiement)
8. [UE5 Server](#8-ue5-server)
9. [CI/CD](#9-cicd)

---

## 1. Vue d'ensemble

### Qu'est-ce que DeepBl4nder ?

DeepBl4nder est un système d'orchestration multi-agents IA pour la production audiovisuelle assistée par ordinateur. Il transforme une intention textuelle (brief créatif) en scène Blender exploitable, puis en séquence animée ou filmée, en suivant un pipeline structuré qui reproduit les étapes réelles d'un studio de production.

### Objectifs

- Transformer une intention textuelle en scène Blender, storyboard, séquence courte ou étude visuelle.
- Découper la production en compétences précises reliées à des agents et sous-agents bien définis.
- Fournir un runtime d'orchestration réutilisable, modulaire et extensible.
- Garantir la traçabilité (provenance, versions), l'observabilité et le contrôle des coûts.
- Garder l'humain dans la boucle à chaque étape où la décision a de la valeur.

### Non-objectifs

- Générer des longs métrages autonomes dès le départ (le MVP vise des séquences de 5 à 10 secondes).
- Remplacer l'expertise d'un studio : DeepBl4nder est une production assistée, pas un remplacement.
- Écrire tout le code d'un coup : l'implémentation suit un chemin incrémental.

### Métriques de succès

| Métrique | Cible |
|----------|-------|
| Latence (brief → premier rendu) | < 5 min (scène de démo), < 10 min (séquence 10s) |
| Coût par scène de démo | < 1 € (LLM + rendu) |
| Taux de passage QA au 1er coup | ≥ 60 % à maturité |
| Workers parallèles | 3 par machine, 1 par scène |
| Reprise après crash | Rejeu des événements non consommés |
| Alerte dépassement budget | < 30 s |

### Framework Agentique

DeepBl4nder repose sur [NVIDIA NeMo Labs OO-Agents (NOOA)](https://github.com/NVIDIA-NeMo/labs-OO-Agents), un framework multi-agents open source. Les agents DeepBl4nder sont des sous-classes directes de `nooa.Agent` — aucun runtime agentique propriétaire n'est réimplémenté.

---

## 2. Architecture technique

### Diagramme haute niveau

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DeepBl4nder — Architecture                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌──────────────────────────────────────────────────┐ │
│  │  Frontend    │    │                API Gateway (FastAPI)            │ │
│  │  Next.js     │───▶│  /api/auth  /api/productions  /api/events      │ │
│  │  :3000       │    │  Auth JWT │ RBAC │ Multi-tenant │ SSE          │ │
│  └─────────────┘    └────────────────────┬─────────────────────────────┘ │
│                                          │                               │
│                                          ▼                               │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                     PipelineRunner (Orchestrateur)                 │  │
│  │                                                                    │  │
│  │  Brief ──▶ Story ──▶ Storyboard ──▶ Director ──▶ Blender          │  │
│  │    │                  │                 │             │             │  │
│  │    │                  ▼                 ▼             ▼             │  │
│  │    │         Character ──▶ Env ──▶ Animation ──▶ Rendu             │  │
│  │    │                                                 │             │  │
│  │    └─────────────────────────────────────────────────▶ QA          │  │
│  │                                                 │                  │  │
│  │    Audio ──▶ Music ──▶ Sound ──▶ Compositing ──▶ Localisation     │  │
│  │    │                                                       │        │  │
│  │    └───────────────────────────────────────────────────────┘        │  │
│  │                                          │                         │  │
│  │                                          ▼                         │  │
│  │                                    Final Review                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                          │                               │
│            ┌─────────────────────────────┼────────────────────────┐      │
│            │                             │                        │      │
│            ▼                             ▼                        ▼      │
│  ┌─────────────────┐   ┌──────────────────────┐   ┌────────────────┐  │
│  │  Worker Blender  │   │  UE5 Server (opt.)   │   │  Frontend UI   │  │
│  │  Docker + GPU    │   │  REST API :8080       │   │  Next.js       │  │
│  │  Blender 4.1     │   │  Unreal Engine 5      │   │  SSE Events    │  │
│  └─────────────────┘   └──────────────────────┘   └────────────────┘  │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Infrastructure                                 │ │
│  │  PostgreSQL 16 │ Redis 7 │ MinIO │ Langfuse │ Celery              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### Pile technologique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| **Langage** | Python 3.12+ | Langage principal |
| **Framework agentique** | NOOA 0.0.8 | Orchestration multi-agents |
| **API** | FastAPI + Uvicorn | Gateway HTTP/REST, SSE |
| **Base de données** | PostgreSQL 16 / SQLite (dev) | Données persistantes |
| **Cache / File d'attente** | Redis 7 | Pub/Sub, Celery broker |
| **Object Storage** | MinIO | Artifacts, rendus |
| **Rendu 3D** | Blender 4.1 (headless) | Scènes, animation, rendu |
| **Rendu vidéo** | FFmpeg | Post-traitement vidéo |
| **Moteur temps réel** | Unreal Engine 5 (optionnel) | Rendu Lumen/Nanite |
| **Frontend** | Next.js | Interface utilisateur |
| **Observabilité LLM** | Langfuse | Traçage des appels LLM |
| **Validation de code** | AST + politique | Sécurité du code généré |
| **Migrations DB** | Alembic | Versioning du schéma |
| **Tests** | Pytest + httpx | Suite de tests |
| **Linting** | Ruff + Mypy | Qualité de code |
| **Conteneurs** | Docker + Docker Compose | Déploiement |
| **CI/CD** | GitHub Actions | Intégration continue |
| **LLM (multi-fournisseurs)** | Gemini, Groq, NVIDIA, OpenRouter, Cloudflare, Local | Génération IA |

### Fournisseurs LLM supportés

| Fournisseur | Modèle par défaut | Variable d'environnement |
|-------------|-------------------|--------------------------|
| Google Gemini | `gemini/gemini-3.6-flash` | `GEMINI_API_KEY` |
| Groq | `groq/openai/gpt-oss-120b` | `GROQ_API_KEY` |
| NVIDIA NIM | `nvidia_nim/meta/llama-3.3-70b-instruct` | `NVIDIA_API_KEY` |
| OpenRouter | `openrouter/meta-llama/llama-3.3-70b-instruct` | `OPENROUTER_API_KEY` |
| Cloudflare Workers AI | `cloudflare/@cf/meta/llama-3.3-70b-instruct` | `CLOUDFLARE_API_KEY` |
| Local (Ollama) | `ollama/llama3` | Aucune |

Le `LLMRouter` supporte deux modes de routage :
- **vote** (défaut) : tous les fournisseurs sains votent, majorité gagne.
- **fallback** : un seul fournisseur sollicité par appel, basculement sur erreur.

Un mécanisme de cooldown simple protège contre les erreurs de taux/quota.

### Composants du package Python

```
deepbl4nder/
├── agents/          # Agents NOOA (Director, Blender, QA, Audio, Compositing, Localization, Story, etc.)
├── api/             # FastAPI app, routes, DB models, auth, pipeline, SSE
├── artifacts/       # Registre d'artifacts, provenance graph
├── bridge/          # WorkerProcess (exécution de processus OS)
├── bridges/blender/ # BlenderBridge (exécution Blender headless)
├── codegen/         # Validateur AST, politique de code
├── domain/          # Objets métier (SceneSpec, ShotSpec, QAReport, StorySpec, etc.)
├── llm.py           # Routeur LLM multi-fournisseurs (LLMRouter)
├── plugins/         # Plugins (Blender, FFmpeg, Audio, TTS, Storage, Subtitle, etc.)
├── production/      # Runner, runs, étapes, événements, budget, reprise
├── skills/          # Registre de skills NOOA (progressive disclosure)
├── cli.py           # CLI (inspect, validate, --version)
├── logging_setup.py # Journalisation arrière-plan (console + fichier rotatif)
└── nooa_compat.py   # Compatibilité enveloppes NOOA
```

---

## 3. Installation et déploiement

### Prérequis

- Docker >= 24.0 + Docker Compose >= 2.24
- Python >= 3.12 (pour le développement local)
- GPU NVIDIA (optionnel, pour le rendu Blender/UE5)

### Installation via Docker (recommandé)

```bash
# 1. Cloner le dépôt
git clone https://github.com/DeepBl4nder/DeepBl4nder.git
cd DeepBl4nder

# 2. Lancer le script d'initialisation
./scripts/setup.sh

# 3. Éditer les variables d'environnement
nano .env

# 4. Démarrer tous les services
docker compose up -d

# 5. Vérifier la santé des services
./scripts/health-check.sh
```

### Services et ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Interface Next.js |
| API | 8000 | FastAPI Gateway |
| API Docs | 8000/docs | Swagger UI |
| PostgreSQL | 5432 | Base de données |
| Redis | 6379 | Cache / File d'attente |
| MinIO Console | 9001 | Object Storage UI |
| MinIO API | 9000 | Object Storage API |
| Langfuse | 3002 | Observabilité LLM |
| UE5 Server | 8080 | Unreal Engine 5 (optionnel) |

### Installation locale (développement)

```bash
# Installer le package en mode édition
pip install -e ".[dev]"

# Linter
python -m ruff check DeepBl4nder tests

# Type check
python -m mypy DeepBl4nder

# Tests
python -m pytest -q

# CLI
DeepBl4nder --version
DeepBl4nder inspect
DeepBl4nder validate mon_script.py
```

### Dépendances optionnelles

| Extra | Package | Usage |
|-------|---------|-------|
| `memory` | `nooa-memory==0.0.8` | Mémoire long terme des agents |
| `sandbox` | `nooa[sandbox]==0.0.8` | Exécution sandboxée |
| `tracing` | `nooa[tracing]==0.0.8` | Tracing NOOA |
| `mcp` | `nooa[mcp]==0.0.8` | Model Context Protocol |
| `vllm` | `vllm>=0.8` | LLM local haute performance |
| `worker` | `psutil` | Monitoring worker |
| `dev` | `ruff, mypy, pytest, httpx>=0.27` | Développement |

### Configuration (.env)

Les variables clés à configurer dans `.env` :

```bash
# Sécurité
DEEPBL4NDER_SECRET_KEY=<64-caractères-minimum>
JWT_SECRET=<secret-jwt>

# Base de données
POSTGRES_PASSWORD=<mot-de-passe-fort>

# LLM (au moins un)
GEMINI_API_KEY=...
GROQ_API_KEY=...
NVIDIA_API_KEY=...

# Budget max par production
DEEPBL4NDER_BUDGET=1.0
```

### Dockerfiles

| Fichier | Image | Usage |
|---------|-------|-------|
| `Dockerfile` | Image runtime de base | Python + Blender + FFmpeg, commande `DeepBl4nder` |
| `Dockerfile.api` | `DeepBl4nder/api` | FastAPI Gateway, non-root, healthcheck |
| `Dockerfile.worker` | `DeepBl4nder/worker` | Blender 4.1 LTS headless + FFmpeg, GPU, non-root |

Le worker installe Blender 4.1.1 depuis le tarball officiel et inclut toutes les bibliothèques graphiques nécessaires au rendu headless (X11, OpenGL, Mesa).

---

## 4. Pipeline de production

Le pipeline suit 14 étapes qui reproduisent le processus réel d'un studio d'animation :

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Pipeline de Production (14 étapes)                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ÉTAPE 1  ─── Brief Créatif ─────────────────────────────────────  │
│  ÉTAPE 2  ─── Scénario / Structure narrative ────────────────────  │
│  ÉTAPE 3  ─── Storyboard ────────────────────────────────────────  │
│  ÉTAPE 4  ─── Prévisualisation (Layout) ─────────────────────────  │
│  ÉTAPE 5  ─── Direction Artistique (SceneSpec) ──────────────────  │
│  ÉTAPE 6  ─── Caractères ────────────────────────────────────────  │
│  ÉTAPE 7  ─── Environnement ─────────────────────────────────────  │
│  ÉTAPE 8  ─── Animation ─────────────────────────────────────────  │
│  ÉTAPE 9  ─── Blender Script (Code bpy) ─────────────────────────  │
│  ÉTAPE 10 ─── Rendu ─────────────────────────────────────────────  │
│  ÉTAPE 11 ─── QA (Contrôle qualité) ─────────────────────────────  │
│  ÉTAPE 12 ─── Audio (Musique + SFX + Voix) ─────────────────────  │
│  ÉTAPE 13 ─── Compositing ───────────────────────────────────────  │
│  ÉTAPE 14 ─── Localisation (Sous-titres + Langues) ─────────────  │
│                                                                     │
│  ┌─── Boucle de révision ──────────────────────────────────────┐   │
│  │  QA échoue → Retour à l'étape ciblée (Director/Blender/...) │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ÉTAPE FINALE ─── Review finale ─────────────────────────────────  │
└─────────────────────────────────────────────────────────────────────┘
```

### Agents du pipeline

| Étape | Agent | Stratégie NOOA | Rôle |
|-------|-------|----------------|------|
| 1-2 | `StoryAgent` | CodeAct | Logline, synopsis, actes, dialogues |
| 3 | `StoryboardAgent` | CodeAct | Plans, cadrage, durée |
| 5 | `DirectorAgent` | CodeAct | SceneSpec, plans, caméra, ambiance |
| 6 | `CharacterDesignerAgent` | CodeAct | Design personnages, géométrie |
| 7 | `EnvironmentArtistAgent` | CodeAct | Environnement, mood, assets |
| 8 | `AnimatorAgent` | CodeAct | Clips d'animation |
| 9 | `BlenderAgent` | Reflexion | Script bpy (génération + réflexion) |
| 10 | Worker Blender | Process | Exécution headless du script |
| 11 | `QAAgent` | Predict | Évaluation visuelle, technique, sémantique |
| 12a | `MusicComposerAgent` | CodeAct | Thème musical, tempo, mood |
| 12b | `SoundDesignerAgent` | CodeAct | SFX, ambiance sonore |
| 13 | `CompositingAgent` | CodeActLite | Passes de rendu, grading |
| 14 | `LocalizationAgent` | CodeAct | Multilingue, sous-titres |
| Finale | `ReviewAgent` | CodeAct | Approbation finale |

### Stratégies NOOA utilisées

- **TemplateStrategy** : code déterministe, zéro appel LLM (ex: script probe Blender).
- **ReflexionStrategy** : boucle génération + évaluation itérative (ex: raffinement de script).
- **PredictStrategy** : un seul tour LLM, sortie typée (ex: scan QA rapide).
- **CodeActLiteStrategy** : exécution de code léger (ex: compositing).

### Gestion des erreurs

- **GenerationError** : les modèles de secours qui s'enlilent sur la validation déclenchent une régénération fraîche (1 retry).
- **Échec storyboard** : synthèse déterministe depuis les beats de l'histoire.
- **Échec Blender** : script bpy synthétisé depuis la SceneSpec.
- **Budget épuisé** : exécution bloquée avant même l'appel aux agents.

### Révision et HITL (Human-In-The-Loop)

Le pipeline supporte la révision humaine via des fichiers `revision_request_*.json` :

1. L'utilisateur soumet un commentaire ciblant une étape spécifique.
2. Le `PipelineRunner` injecte le commentaire comme `revision_feedback` dans le contexte NOOA de l'agent ciblé.
3. L'étape ciblée et les étapes en aval sont rejouées.
4. Les étapes amont sont reprises depuis les checkpoints (pas de re-génération inutile).
5. La demande de révision est consommée (renommée `.applied.json`) après un run terminé.

### Reprise après crash

Le système supporte la reprise complète :
- **EventLog** : journal JSONL séquentiel (append-only, tolerant aux lignes corrompues).
- **Checkpoints** : état du run persisté (`run_state.json`, `scene_spec.json`, `script.py`).
- **Recovery** : `ProductionRun.recover()` reconstruit l'état depuis le journal.
- **Invalidation** : un changement de brief invalide les checkpoints et force un rejeu complet.

---

## 5. Base de données

### Schéma conceptuel

La base de données gère le socle SaaS multi-tenant :

```
┌──────────────────────────────────────────────────────────────────┐
│                     Schéma de la base de données                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User ──────────┐                                               │
│    │             │                                               │
│    │          Membership (role: owner/admin/editor/viewer)       │
│    │             │                                               │
│    │          Organization ──┐                                   │
│    │             │            │                                   │
│    │          Workspace ─────┤                                   │
│    │             │            │                                   │
│    │          Project ───────┤                                   │
│    │             │            │                                   │
│    │          Production ────┘                                   │
│    │             │                                               │
│    └─────────────┘                                               │
│                                                                  │
│  Production:                                                     │
│    ├── name, brief, status (draft/queued/running/completed/...)  │
│    ├── version (incrémentée à chaque run)                        │
│    ├── progress (0.0 → 1.0)                                     │
│    ├── workdir (chemin vers les artifacts)                       │
│    └── finished_at                                               │
│                                                                  │
│  Artifacts (registre en mémoire + disque):                       │
│    ├── id, type, name, path, version, sha256, status, cost      │
│    └── provenance (graphe dirigé: parent → enfant)               │
└──────────────────────────────────────────────────────────────────┘
```

### Isolation multi-tenant

- Chaque ressource (Organization, Workspace, Project, Production) est scopée par son propriétaire.
- Les requêtes passent par des filtres tenant qui retournent 404 (pas de fuite d'existence).
- Les rôles RBAC : `owner` > `admin` > `editor` > `viewer`.

### Migrations Alembic

```bash
# Générer une migration après changement de modèle
alembic revision --autogenerate -m "description"

# Appliquer les migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

Le fichier `alembic/env.py` lit l'URL de la base depuis la variable `DEEPBL4NDER_DB` ou fallback SQLite.

### Données non relationnelles

| Stockage | Technologie | Contenu |
|----------|-------------|---------|
| Fichiers run | Disque (`/work`, `/projects`) | Scripts, rendus, frames, JSON |
| EventLog | JSONL sur disque | Journal d'événements append-only |
| Object Storage | MinIO | Artifacts binaires, rendus finaux |
| Cache | Redis | Sessions, routing stats, pub/sub |

---

## 6. Tests

### Vue d'ensemble de la suite de tests

La suite compte **18 fichiers de test** couvrant l'ensemble des composants :

| Fichier | Module testé | Nombre de tests | Description |
|---------|-------------|-----------------|-------------|
| `test_domain.py` | `domain/` | 7 | Objets métier : SceneSpec, ShotSpec, QAReport, CharacterSpec, SHA256 |
| `test_artifacts.py` | `artifacts/` | 5 | Registre d'artifacts, versioning, hash, provenance |
| `test_codegen.py` | `codegen/` | 7 | Validateur AST, politique de code, imports interdits |
| `test_bridge.py` | `bridge/` + `bridges/` | 5 | WorkerProcess, BlenderBridge, fail-closed |
| `test_cli.py` | `cli.py` | 4 | Commandes CLI : inspect, validate, --version |
| `test_llm.py` | `llm.py` | 40+ | Routeur LLM, vote, fallback, cooldown, découverte, classification erreurs |
| `test_runner.py` | `production/runner.py` | 18+ | Pipeline complet, révisions, budget, reprise, checkpoint, synthèse |
| `test_production.py` | `production/` | 12 | Runs, étapes, événements, budget, alertes, récupération |
| `test_decoupling.py` | Architecture | 10 | Découplage NOOA, pas de réimplémentation générique |
| `test_nooa_capabilities.py` | `agents/` | 12 | Capacités NOOA : Template, Reflexion, Predict, CodeActLite, mémoire, events |
| `test_nooa_compat.py` | `nooa_compat.py` | 18 | Compatibilité enveloppes NOOA, coercition, réparations |
| `test_saas_api.py` | `api/` | 20+ | Auth, RBAC, CRUD, pipeline E2E, SSE, CORS, revision, preview |
| `test_plugins.py` | `plugins/` | 14 | Plugins (Blender, Audio, Storage, Subtitle, AssetLibrary, KnowledgeGraph) |
| `test_scheduler.py` | `bridges/scheduler.py` | 4 | WorkerScheduler : soumission, parallélisme, ajout à chaud |
| `test_media.py` | `domain/media.py` | 5 | AudioPlan, AudioMaster, CompositeSpec, LanguagePackage |
| `test_skills.py` | `skills/` | 4 | Découverte, chargement, progressive disclosure |
| `test_seed.py` | `api/seed.py` | 4 | Seed admin, idempotence, reset mot de passe |
| `test_logging_setup.py` | `logging_setup.py` | 2 | Journalisation fichier rotatif, idempotence |

### Comment exécuter les tests

```bash
# Tous les tests
python -m pytest -q

# Avec couverture
python -m pytest --cov=DeepBl4nder --cov-report=term-missing

# Un fichier spécifique
python -m pytest tests/test_llm.py -v

# Un test spécifique
python -m pytest tests/test_runner.py::test_happy_path_produces_traced_run -v

# Sans réseau (la plupart des tests)
python -m pytest -q  # Les tests LLM utilisent des stubs/mock
```

### Stratégie de test

- **Pas de dépendance réseau** : tous les tests LLM utilisent `FakeLLMClient` ou des stubs.
- **Tests d'intégration** : `test_runner.py` teste le pipeline complet avec des agents stub.
- **Tests E2E API** : `test_saas_api.py` utilise `TestClient` de FastAPI.
- **Invariantes structurels** : `test_decoupling.py` vérifie que le domaine n'importe jamais NOOA.
- **Régressions** : de nombreux tests portent des commentaires de régression (logs datés).

---

## 7. Scripts de déploiement

Le répertoire `scripts/` contient 4 scripts Bash de gestion :

### `setup.sh` — Initialisation

```bash
./scripts/setup.sh
```

- Vérifie les prérequis (Docker, Docker Compose).
- Crée `.env` depuis `.env.production` si absent.
- Crée les répertoires `work/`, `projects/`, `data/`.
- Configure le bucket MinIO si le client `mc` est disponible.

### `deploy.sh` — Déploiement production

```bash
./scripts/deploy.sh [staging|production]
```

- Pull des dernières images Docker.
- Build des images custom (sans cache).
- Arrêt des services existants.
- Démarrage de l'infrastructure (PostgreSQL, Redis, MinIO).
- Exécution des migrations Alembic.
- Démarrage de tous les services.
- Vérification santé API et Frontend.

### `health-check.sh` — Vérification santé

```bash
./scripts/health-check.sh
```

Vérifie la disponibilité de tous les services :
- API (port 8000)
- Frontend (port 3000)
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (port 9000)
- Langfuse (port 3002, optionnel)
- UE5 Server (port 8080, optionnel)

### `backup.sh` — Sauvegarde

```bash
./scripts/backup.sh [répertoire_de_sauvegarde]
```

- Dump PostgreSQL compressé (gzip).
- Archive MinIO (tar.gz).
- Sauvegarde des fichiers de configuration (`.env`, `docker-compose.yml`).

---

## 8. UE5 Server

### Architecture

```
DeepBl4nder API ──▶ UE5Bridge ──▶ REST API (ce serveur) ──▶ UE5 Python API ──▶ UE5 Editor
```

Le serveur UE5 est une API FastAPI autonome qui communique avec l'éditeur Unreal Engine 5 via son API Python. Il doit s'exécuter sur une machine où UE5 est installé.

### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Santé du serveur + disponibilité UE5 |
| POST | `/level/create` | Créer un level |
| POST | `/level/delete` | Supprimer un level |
| POST | `/asset/import` | Importer un asset (.fbx, .gltf, .glb) |
| POST | `/actor/create` | Créer un acteur |
| POST | `/material/create` | Créer un matériau PBR Lumen |
| POST | `/material/apply` | Appliquer un matériau |
| POST | `/lighting/setup` | Configurer l'éclairage Lumen |
| POST | `/light/create` | Créer une lumière |
| POST | `/sequencer/setup` | Configurer le Sequencer |
| POST | `/sequencer/add_camera` | Ajouter une piste caméra |
| POST | `/sequencer/add_actor_track` | Ajouter une piste d'animation |
| POST | `/render/start` | Lancer un rendu MRQ |
| GET | `/render/status` | Statut du rendu en cours |
| POST | `/render/cancel` | Annuler le rendu |
| POST | `/cvar/set` | Définir une console variable UE5 |
| POST | `/quality/preset` | Appliquer un preset qualité |

### Presets de qualité

| Preset | Lumen GI | Nanite | Screen % | Ombres | Motion Blur |
|--------|----------|--------|----------|--------|-------------|
| low | OFF | OFF | - | - | - |
| medium | ON | ON | - | - | - |
| high | ON | ON | 100 | - | - |
| epic | ON | ON | 100 | 5 | - |
| cinematic | ON | ON | 150 | 5 | 4 |

### Installation

```bash
# Via Docker Compose (profile "ue5")
docker compose --profile ue5 up -d

# Ou manuellement
cd ue5-server
pip install -r requirements.txt
python server.py
```

Le serveur écoute sur le port **8080**. Les endpoints sont actuellement stubbés (les appels UE5 Python API sont commentés) — l'implémentation réelle nécessite une instance UE5 avec le plugin Python activé.

---

## 9. CI/CD

### Workflow GitHub Actions

Le fichier `.github/workflows/ci.yml` définit 5 jobs :

```
┌──────────────────────────────────────────────────────────────────┐
│                    Pipeline CI/CD GitHub Actions                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Job 1: lint-typecheck-test                                     │
│  ├── Ruff (linting Python)                                      │
│  ├── Mypy (vérification de types)                               │
│  └── Pytest (tests unitaires)                                   │
│           │                                                      │
│           ▼                                                      │
│  Job 2: docker-build (push uniquement)                          │
│  ├── Build Dockerfile.api ──▶ ghcr.io/.../api                   │
│  └── Build Dockerfile.worker ──▶ ghcr.io/.../worker             │
│           │                                                      │
│  Job 3: docker-build-frontend (push uniquement)                 │
│  └── Build frontend/Dockerfile ──▶ ghcr.io/.../frontend         │
│           │                                                      │
│           ▼                                                      │
│  Job 4: integration-test (push uniquement)                      │
│  ├── Créer .env de test                                         │
│  ├── Démarrer PostgreSQL, Redis, MinIO                          │
│  ├── Démarrer l'API                                             │
│  ├── Health check                                               │
│  └── Pytest dans le conteneur                                   │
│           │                                                      │
│           ▼                                                      │
│  Job 5: deploy (main uniquement)                                │
│  └── Déploiement SSH (configurable)                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Déclencheurs

- **push** sur `main` ou `master` : tous les jobs.
- **pull_request** : uniquement `lint-typecheck-test`.

### Stratégie de build Docker

- Registry : `ghcr.io` (GitHub Container Registry).
- Tags : SHA du commit, branche, `latest` (branche par défaut).
- Cache : GitHub Actions cache (`type=gha`).
- Build matrix : `api` + `worker` en parallèle, `frontend` séparé.

### Déploiement

Le déploiement est automatique sur push vers `main`, après validation de tous les tests. Le step de déploiement est un placeholder configurable (SSH, Kubernetes, AWS ECS, Google Cloud Run, etc.).

### Qualité de code

| Outil | Commande | Seuil |
|-------|----------|-------|
| Ruff | `python -m ruff check DeepBl4nder tests` | 0 erreur |
| Mypy | `python -m mypy DeepBl4nder` | 0 erreur |
| Pytest | `python -m pytest -q` | 100% passage |

---

## Annexe A : Compétences couvertes par les agents

| Compétence | Agent principal |
|------------|-----------------|
| Narration et structure dramatique | StoryAgent |
| Écriture de dialogues | StoryAgent |
| Storyboard | StoryboardAgent |
| Composition visuelle | DirectorAgent |
| Création et gestion d'assets | CharacterDesignerAgent, EnvironmentArtistAgent |
| Animation | AnimatorAgent |
| Caméra et cadrage | DirectorAgent |
| Éclairage et ambiance | DirectorAgent, EnvironmentArtistAgent |
| Sound design | SoundDesignerAgent |
| Musique et mixage | MusicComposerAgent |
| Voix et localization | LocalizationAgent |
| Contrôle qualité | QAAgent |
| Rendu 3D | BlenderAgent + Worker Blender |
| Compositing | CompositingAgent |

## Annexe B : Cas d'usage

- Générer une scène Blender à partir d'un brief textuel.
- Créer un storyboard simple avant animation.
- Produire une animatique pour prévisualiser un épisode ou un court métrage.
- Préparer une séquence stylisée type anime, cartoon ou semi-réaliste.
- Étudier rapidement plusieurs variantes de décor, d'éclairage ou de caméra.
- Évaluer si une idée est réalisable techniquement dans un délai donné.
- Aider un créateur à itérer plus vite sur le décor, la caméra et le mouvement.
- Ajouter une piste audio, des effets sonores et une musique d'ambiance.
- Gérer plusieurs langues pour les dialogues, les sous-titres et l'interface.

## Annexe C : Exemples

### Exécution du Director (LLM réel)

```bash
python examples/run_director.py
```

Utilise Gemini par défaut pour transformer un brief en `SceneSpec`.

### Pipeline complet (Brief → Script bpy)

```bash
python examples/run_pipeline.py
```

Génère un script Blender à partir d'un brief, puis valide le code via le validateur AST.

---

*Cette documentation estmaintenue par l'équipe DeepBl4nder. Pour toute question, consulter le README racine ou ouvrir un ticket.*


