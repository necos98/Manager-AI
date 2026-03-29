#!/bin/sh
set -e

cd /app/backend

# Run database migrations
echo "[...] Running database migrations..."
python -m alembic upgrade head
echo "[ok] Migrations complete"

# Start the application
echo "[...] Starting Manager AI on port ${BACKEND_PORT:-8000}..."
exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${BACKEND_PORT:-8000}"
