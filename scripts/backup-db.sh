#!/bin/bash
# VULKRAN OS — PostgreSQL daily backup script
# Usage: Add to crontab: 0 4 * * * /root/vulkran-os/scripts/backup-db.sh

set -euo pipefail

BACKUP_DIR="/root/vulkran-os/backups"
COMPOSE_DIR="/root/vulkran-os"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/vulkran_${TIMESTAMP}.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Dump database via docker compose
docker compose -f "${COMPOSE_DIR}/docker-compose.yml" exec -T db \
    pg_dump -U vulkran -d vulkrandb --no-owner --no-privileges \
    | gzip > "$BACKUP_FILE"

# Verify backup was created and is not empty
if [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file is empty or was not created: $BACKUP_FILE"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "OK: Backup created: $BACKUP_FILE ($BACKUP_SIZE)"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "vulkran_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "Cleaned up backups older than ${RETENTION_DAYS} days"
