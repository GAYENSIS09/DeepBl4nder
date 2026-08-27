#!/usr/bin/env bash
# DeepBlender — Deploy to Production
#
# Usage:
#   ./scripts/deploy.sh [environment]
#
# Environments: production, staging

set -euo pipefail

ENVIRONMENT="${1:-production}"
echo "=== DeepBlender Deploy ($ENVIRONMENT) ==="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Error: docker not found"; exit 1; }

# Check .env
if [ ! -f .env ]; then
    echo "Error: .env file not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Pull latest images
echo "Pulling latest images..."
docker compose pull

# Build custom images
echo "Building images..."
docker compose build --no-cache

# Stop existing services
echo "Stopping existing services..."
docker compose down

# Start infrastructure
echo "Starting infrastructure..."
docker compose up -d postgres redis minio
sleep 10

# Run database migrations (if needed)
echo "Running database migrations..."
docker compose run --rm deepblender-api python -m alembic upgrade head 2>/dev/null || true

# Start all services
echo "Starting all services..."
docker compose up -d

# Wait for health checks
echo "Waiting for services to be healthy..."
sleep 20

# Verify
echo "Verifying services..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed"
    docker compose logs deepblender-api --tail=20
    exit 1
fi

if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "⚠️  Frontend health check failed (may still be starting)"
fi

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Langfuse:  http://localhost:3002"
echo "  MinIO:     http://localhost:9001"
echo ""
echo "Logs: docker compose logs -f"
echo "Stop: docker compose down"
