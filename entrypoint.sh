#!/bin/bash
set -e

echo "Running database migrations..."
python -m migrations.run

echo "Starting chunk processor..."
python -m processor.tick &
PROCESSOR_PID=$!

cleanup() {
    echo "Shutting down..."
    kill "$PROCESSOR_PID" 2>/dev/null || true
    wait "$PROCESSOR_PID" 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

echo "Starting gunicorn..."
exec gunicorn \
    --bind "0.0.0.0:5050" \
    --workers "${GUNICORN_WORKERS:-4}" \
    --threads 2 \
    --timeout "${GUNICORN_TIMEOUT:-300}" \
    --access-logfile - \
    --error-logfile - \
    app:app
