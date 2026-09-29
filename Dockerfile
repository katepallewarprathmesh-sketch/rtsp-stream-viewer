# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python runtime with FFmpeg ----------
FROM python:3.12-slim

# ffmpeg: transcoding | fonts: drawtext overlay for demo cams | curl: mediamtx download
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fontconfig fonts-dejavu-core curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# MediaMTX: lightweight RTSP server used only for the optional built-in
# demo streams (DEMO_MODE=1). Not required for viewing external cameras.
ARG MEDIAMTX_VERSION=v1.9.3
RUN curl -sL "https://github.com/bluenviron/mediamtx/releases/download/${MEDIAMTX_VERSION}/mediamtx_${MEDIAMTX_VERSION}_linux_amd64.tar.gz" \
    | tar xz -C /usr/local/bin mediamtx

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
# settings.py resolves the frontend build at ../frontend/dist relative to backend/
COPY --from=frontend /app/dist /app/frontend/dist

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PORT=8000 \
    DEMO_MODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["/entrypoint.sh"]
