#!/usr/bin/env bash
# DeepBlender — Initial Setup
#
# Usage:
#   ./scripts/setup.sh

set -euo pipefail

echo "=== DeepBlender Setup ==="

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Error: docker not found"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Error: docker compose not found"; exit 1; }

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.production..."
    cp .env.production .env
    echo "⚠️  Please edit .env and fill in your API keys and secrets"
else
    echo ".env already exists"
fi

# Create required directories
echo "Creating directories..."
mkdir -p work projects data

# Create MinIO bucket (if minio client available)
if command -v mc >/dev/null 2>&1; then
    echo "Setting up MinIO bucket..."
    mc alias set local http://localhost:9000 deepblender minioadmin 2>/dev/null || true
    mc mb local/deepblender 2>/dev/null || true
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: docker compose up -d"
echo "  3. Open: http://localhost:3000 (frontend)"
echo "  4. API: http://localhost:8000/docs"
echo ""
echo "Optional services:"
echo "  - UE5: docker compose --profile ue5 up -d"
echo "  - Langfuse: http://localhost:3002"
echo "  - MinIO: http://localhost:9001"
