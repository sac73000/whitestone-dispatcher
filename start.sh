#!/bin/bash

export APP_USERNAME="${APP_USERNAME:-WSE}"
export APP_PASSWORD="${APP_PASSWORD:-WhiteStoneGeo}"
export SECRET_KEY="${SECRET_KEY:-change-this-to-a-random-string}"
export DB_PATH="${DB_PATH:-./whitestone.db}"
export LOG_FILE="${LOG_FILE:-./app.log}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5000}"
WORKERS="${WORKERS:-2}"

echo "Starting WHITE STONE GEOMATICS Crew Scheduler..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo "  Database: $DB_PATH"
echo "  Log file: $LOG_FILE"

gunicorn \
    --bind "${HOST}:${PORT}" \
    --workers "${WORKERS}" \
    --threads 2 \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    main:app
