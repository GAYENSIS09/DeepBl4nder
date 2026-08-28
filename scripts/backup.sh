#!/usr/bin/env bash
# DeepBl4nder — Backup
#
# Usage:
#   ./scripts/backup.sh [backup_dir]

set -euo pipefail

BACKUP_DIR="${1:-./backups/$(date +%Y%m%d_%H%M%S)}"
echo "=== DeepBl4nder Backup ==="
echo "Backup directory: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

# PostgreSQL
echo "Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U DeepBl4nder DeepBl4nder | gzip > "$BACKUP_DIR/postgres.sql.gz"

# MinIO data
echo "Backing up MinIO data..."
docker compose exec -T minio tar czf /tmp/minio-backup.tar.gz /data 2>/dev/null || true
docker compose cp minio:/tmp/minio-backup.tar.gz "$BACKUP_DIR/minio-data.tar.gz" 2>/dev/null || true

# Config files
echo "Backing up config..."
cp .env "$BACKUP_DIR/env-backup" 2>/dev/null || true
cp docker-compose.yml "$BACKUP_DIR/docker-compose.yml"

echo ""
echo "=== Backup Complete ==="
echo "Location: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"

