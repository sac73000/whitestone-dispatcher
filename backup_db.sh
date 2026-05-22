#!/bin/bash

DB_PATH="${DB_PATH:-./whitestone.db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

cp "$DB_PATH" "$BACKUP_DIR/whitestone_${TIMESTAMP}.db"
echo "Database backed up to: $BACKUP_DIR/whitestone_${TIMESTAMP}.db"

sqlite3 "$DB_PATH" .dump > "$BACKUP_DIR/whitestone_${TIMESTAMP}.sql"
echo "SQL dump saved to: $BACKUP_DIR/whitestone_${TIMESTAMP}.sql"

KEEP=10
cd "$BACKUP_DIR"
ls -t whitestone_*.db 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm
ls -t whitestone_*.sql 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm
echo "Cleanup complete (keeping last $KEEP backups)"
