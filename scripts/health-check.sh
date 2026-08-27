#!/usr/bin/env bash
# DeepBlender — Health Check
#
# Usage:
#   ./scripts/health-check.sh

set -euo pipefail

echo "=== DeepBlender Health Check ==="

STATUS=0

# API
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API (port 8000)"
else
    echo "❌ API (port 8000)"
    STATUS=1
fi

# Frontend
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend (port 3000)"
else
    echo "❌ Frontend (port 3000)"
    STATUS=1
fi

# PostgreSQL
if docker compose exec -T postgres pg_isready -U deepblender > /dev/null 2>&1; then
    echo "✅ PostgreSQL (port 5432)"
else
    echo "❌ PostgreSQL (port 5432)"
    STATUS=1
fi

# Redis
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis (port 6379)"
else
    echo "❌ Redis (port 6379)"
    STATUS=1
fi

# MinIO
if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "✅ MinIO (port 9000)"
else
    echo "❌ MinIO (port 9000)"
    STATUS=1
fi

# Langfuse (optional)
if curl -sf http://localhost:3002 > /dev/null 2>&1; then
    echo "✅ Langfuse (port 3002)"
else
    echo "⚠️  Langfuse (port 3002) - not running"
fi

# UE5 Server (optional)
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ UE5 Server (port 8080)"
else
    echo "⚠️  UE5 Server (port 8080) - not running"
fi

echo ""
if [ $STATUS -eq 0 ]; then
    echo "=== All core services healthy ==="
else
    echo "=== Some services are down ==="
fi

exit $STATUS
