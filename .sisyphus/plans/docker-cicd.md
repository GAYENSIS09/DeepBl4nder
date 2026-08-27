# Plan : Docker Complet + CI/CD pour DeepBl4nder

## Contexte

Le setup Docker actuel est minimal : 3 services (worker, scheduler, API) sans PostgreSQL, Redis, MinIO, Langfuse, ni UE5. Le CI/CD fait juste lint+test. Il faut un setup production-ready avec tous les prérequis.

## État actuel

| Fichier | Contenu |
|---------|---------|
| `Dockerfile` | Python 3.12 + Blender + FFmpeg (basique) |
| `Dockerfile.worker` | Blender 4.1 from tarball + DeepBl4nder |
| `docker-compose.yml` | 3 services, pas de DB/Redis/UE5 |
| `.github/workflows/ci.yml` | lint + typecheck + test |
| `.env.example` | Variables LLM + binaires |

---

## Étape 1 : Docker Compose Production

**Fichier** : `docker-compose.yml` (réécriture complète)

### Services

```yaml
services:
  # ── Infrastructure ──────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: DeepBl4nder
      POSTGRES_USER: DeepBl4nder
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    healthcheck: pg_isready

  redis:
    image: redis:7-alpine
    volumes: [redis_data:/data]
    healthcheck: redis-cli ping

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]
    ports: ["9000:9000", "9001:9001"]

  # ── Observabilité ───────────────────────────────────────
  langfuse:
    image: langfuse/langfuse:latest
    ports: ["3002:3000"]
    depends_on: [postgres]
    environment:
      DATABASE_URL: postgresql://DeepBl4nder:${POSTGRES_PASSWORD}@postgres:5432/DeepBl4nder
      NEXTAUTH_URL: http://localhost:3002
      NEXTAUTH_SECRET: ${LANGFUSE_SECRET}
      SALT: ${LANGFUSE_SALT}

  # ── DeepBl4nder ─────────────────────────────────────────
  DeepBl4nder-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports: ["8000:8000"]
    depends_on: [postgres, redis, minio]
    environment: *DeepBl4nder-env
    restart: unless-stopped

  DeepBl4nder-worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes: [./work:/work, ./projects:/projects]
    environment: *DeepBl4nder-env
    restart: unless-stopped

  DeepBl4nder-scheduler:
    build:
      context: .
      dockerfile: Dockerfile.worker
    command: python -m DeepBl4nder.tasks.celery_config
    depends_on: [redis, DeepBl4nder-worker]
    environment: *DeepBl4nder-env
    restart: unless-stopped

  # ── UE5 Server (optionnel) ─────────────────────────────
  ue5-server:
    build:
      context: ./ue5-server
      dockerfile: Dockerfile
    ports: ["8080:8080"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      UE5_EXE: /opt/UnrealEngine/Engine/Binaries/Linux/UnrealEditor-Cmd
    restart: unless-stopped
    profiles: ["ue5"]

  # ── Frontend ────────────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports: ["3000:3000"]
    depends_on: [DeepBl4nder-api]
    restart: unless-stopped

volumes:
  pgdata:
  redis_data:
  minio_data:
```

### Anchor pour variables d'environnement

```yaml
x-DeepBl4nder-env: &DeepBl4nder-env
  DeepBl4nder_DB: postgresql://DeepBl4nder:${POSTGRES_PASSWORD}@postgres:5432/DeepBl4nder
  REDIS_URL: redis://redis:6379/0
  MINIO_ENDPOINT: minio:9000
  MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
  MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
  DeepBl4nder_SECRET_KEY: ${DeepBl4nder_SECRET_KEY}
  GROQ_API_KEY: ${GROQ_API_KEY}
  GEMINI_API_KEY: ${GEMINI_API_KEY}
  OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
  NVIDIA_API_KEY: ${NVIDIA_API_KEY}
  CLOUDFLARE_API_KEY: ${CLOUDFLARE_API_KEY}
  CLOUDFLARE_ACCOUNT_ID: ${CLOUDFLARE_ACCOUNT_ID}
  LANGFUSE_SECRET_KEY: ${LANGFUSE_SECRET_KEY}
  LANGFUSE_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY}
  LANGFUSE_HOST: http://langfuse:3000
  BLENDER_EXE: /usr/local/bin/blender
  FFMPEG_EXE: /usr/local/bin/ffmpeg
  DeepBl4nder_ENV: production
```

---

## Étape 2 : Dockerfiles

### 2a. `Dockerfile.api` (NOUVEAU)

```dockerfile
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY DeepBl4nder/ DeepBl4nder/
RUN pip install --no-cache-dir ".[worker]"

# API specific
EXPOSE 8000
ENV PYTHONUNBUFFERED=1 \
    DeepBl4nder_API=1

HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "DeepBl4nder.api.app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2b. `Dockerfile.worker` (mis à jour)

- Ajouter FFmpeg (manquant)
- Ajouter curl pour healthcheck
- Fixer la healthcheck (syntaxe Blender incorrecte)

### 2c. `frontend/Dockerfile` (NOUVEAU)

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

### 2d. `ue5-server/Dockerfile` (NOUVEAU)

```dockerfile
FROM ubuntu:22.04

# Install UE5 dependencies
RUN apt-get update && apt-get install -y \
    libx11-6 libxcursor1 libxinerama1 libxrandr2 libxi6 \
    libgl1-mesa-glx libglu1-mesa libasound2 libpulse0 \
    && rm -rf /var/lib/apt/lists/*

# Copy UE5 server plugin
COPY . /ue5-server
WORKDIR /ue5-server

# Install Python dependencies
RUN pip install fastapi uvicorn requests

EXPOSE 8080
CMD ["python", "server.py"]
```

---

## Étape 3 : `.env.production` (template)

```env
# Database
POSTGRES_PASSWORD=change-me-in-production
DeepBl4nder_SECRET_KEY=change-me-64-chars

# Object Storage
MINIO_ACCESS_KEY=DeepBl4nder
MINIO_SECRET_KEY=change-me-minio

# LLM Keys
GROQ_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
NVIDIA_API_KEY=
CLOUDFLARE_API_KEY=
CLOUDFLARE_ACCOUNT_ID=

# Observability
LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SALT=change-me
```

---

## Étape 4 : CI/CD Pipeline

**Fichier** : `.github/workflows/ci.yml` (réécriture)

### Jobs

```yaml
jobs:
  # ── Quality Gate ────────────────────────────────────────
  lint-typecheck-test:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-python 3.12
      - pip install -e ".[dev]"
      - ruff check
      - mypy DeepBl4nder
      - pytest -q

  # ── Docker Build ────────────────────────────────────────
  docker-build:
    needs: lint-typecheck-test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api, worker]
    steps:
      - checkout
      - docker/setup-buildx
      - docker/login (GHCR)
      - docker/build-push
        file: Dockerfile.${{ matrix.service }}
        tags: ghcr.io/${{ github.repository }}/${{ matrix.service }}:${{ github.sha }}

  # ── Integration Test ────────────────────────────────────
  integration-test:
    needs: docker-build
    runs-on: ubuntu-latest
    steps:
      - checkout
      - docker compose up -d
      - docker compose exec api python -m pytest tests/
      - docker compose down

  # ── Deploy ──────────────────────────────────────────────
  deploy:
    needs: integration-test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - deploy to production (SSH, k8s, or cloud)
```

---

## Étape 5 : UE5 Server Plugin

**Dossier** : `ue5-server/` (NOUVEAU)

Le serveur UE5 est un script Python qui tourne DANS l'éditeur UE5 et expose une API REST.

```
ue5-server/
├── Dockerfile
├── server.py          # FastAPI server
├── endpoints/
│   ├── __init__.py
│   ├── level.py       # Level creation
│   ├── asset.py       # Asset import
│   ├── material.py    # Material creation (Lumen)
│   ├── lighting.py    # Lighting setup
│   ├── sequencer.py   # Animation
│   └── render.py      # MRQ render
├── requirements.txt
└── README.md
```

---

## Étape 6 : Scripts de déploiement

**Dossier** : `scripts/` (NOUVEAU)

```
scripts/
├── deploy.sh          # Deploy production
├── setup.sh           # Initial setup (env, db, etc.)
├── backup.sh          # Backup database + minio
└── health-check.sh    # Verify all services
```

---

## Résumé des fichiers

| Fichier | Action |
|---------|--------|
| `docker-compose.yml` | RÉÉCRIRE — services complets |
| `Dockerfile.api` | CRÉER |
| `Dockerfile.worker` | MODIFIER — ajouter FFmpeg, fix healthcheck |
| `frontend/Dockerfile` | CRÉER |
| `ue5-server/Dockerfile` | CRÉER |
| `ue5-server/server.py` | CRÉER |
| `ue5-server/endpoints/*.py` | CRÉER |
| `.env.production` | CRÉER |
| `.github/workflows/ci.yml` | RÉÉCRIRE — stages complets |
| `scripts/deploy.sh` | CRÉER |
| `scripts/setup.sh` | CRÉER |
| `scripts/health-check.sh` | CRÉER |

## Prérequis GPU

Pour Blender + UE5 en GPU, le docker host doit avoir :
- `nvidia-container-toolkit` installé
- Docker daemon configuré avec `--gpus` support
- Sufficient VRAM (Blender: 4GB+, UE5: 8GB+)

## Risques

- **UE5 Docker image** : UE5 fait 50GB+, l'image Docker sera énorme → utiliser un volume externe ou un image pré-construit
- **GPU pas disponible en CI** : les tests GPU nécessitent un runner self-hosted avec GPU
- **Licence UE5** : redistribution UE5 peut nécessiter une licence Epic Games
- **Backup Minio** : les assets stockés doivent être backupés régulièrement
