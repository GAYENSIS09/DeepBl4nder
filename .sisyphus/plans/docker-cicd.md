# Plan : Docker Complet + CI/CD pour DeepBl4nder

## Contexte

Le setup Docker actuel est minimal : 3 services (worker, scheduler, API) sans PostgreSQL, Redis, MinIO, Langfuse. Le CI/CD fait juste lint+test. Il faut un setup production-ready avec tous les prérequis.

## État actuel

| Fichier | Contenu |
|---------|---------|
| `Dockerfile` | Python 3.12 + Blender + FFmpeg (basique) |
| `Dockerfile.worker` | Blender 4.1 from tarball + DeepBl4nder |
| `docker-compose.yml` | 3 services, pas de DB/Redis |
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

## Étape 5 : Scripts de déploiement

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
| `.env.production` | CRÉER |
| `.github/workflows/ci.yml` | RÉÉCRIRE — stages complets |
| `scripts/deploy.sh` | CRÉER |
| `scripts/setup.sh` | CRÉER |
| `scripts/health-check.sh` | CRÉER |

## Prérequis GPU

Pour le rendu Blender en GPU, le docker host doit avoir :
- `nvidia-container-toolkit` installé
- Docker daemon configuré avec `--gpus` support
- Sufficient VRAM (Blender: 4GB+)

## Risques

- **GPU pas disponible en CI** : les tests GPU nécessitent un runner self-hosted avec GPU
- **Backup Minio** : les assets stockés doivent être backupés régulièrement
