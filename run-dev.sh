#!/usr/bin/env bash
# One-command local run: builds the frontend and starts the backend on :8000.
set -e
cd "$(dirname "$0")"

command -v ffmpeg >/dev/null || { echo "ERROR: ffmpeg is required (sudo apt install ffmpeg)"; exit 1; }

echo "==> Building frontend..."
(cd frontend && npm install --silent && npm run build)

echo "==> Installing backend deps..."
pip install -q -r backend/requirements.txt

echo "==> Starting server on http://localhost:8000"
cd backend
exec python -m daphne -b 0.0.0.0 -p 8000 core.asgi:application
