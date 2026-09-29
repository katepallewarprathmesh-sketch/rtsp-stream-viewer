# RTSP Stream Viewer

A full-stack web application for viewing live RTSP camera streams in the
browser. Add any number of RTSP URLs and watch them simultaneously in a
responsive grid, with per-stream play/pause controls and clear error
reporting.

Built for the **Skylark Labs — Full Stack Engineer Coding Test**.

## Architecture

```
┌──────────────┐   WebSocket (JPEG frames + JSON status)   ┌───────────────────┐
│  React (Vite)│ ◄───────────────────────────────────────► │  Django + Channels │
│  StreamPlayer│                                           │  (Daphne / ASGI)   │
└──────────────┘                                           └─────────┬─────────┘
                                                                     │ spawns one
                                                                     │ process per viewer
                                                               ┌─────▼─────┐   RTSP/TCP   ┌──────────┐
                                                               │  FFmpeg   │ ◄──────────► │ IP camera │
                                                               └───────────┘              └──────────┘
```

**How it works**

1. The React frontend opens one WebSocket per stream tile to
   `/ws/stream/` and sends `{"action": "play", "url": "rtsp://..."}`.
2. The Django Channels consumer validates the URL and spawns a dedicated
   FFmpeg subprocess that pulls the RTSP feed (over TCP for reliability)
   and transcodes it to MJPEG piped to stdout.
3. The consumer parses complete JPEG frames from the pipe and pushes them
   to the browser as binary WebSocket messages; the frontend renders them
   into an `<img>` via object URLs (old URLs are revoked — no memory leaks).
4. Status/error events (`connecting`, `live`, `paused`, plus human-readable
   failure reasons parsed from FFmpeg's stderr) are sent as JSON text frames.

**Why MJPEG-over-WebSocket?** It requires no client-side decoder or MSE
plumbing, works in every browser, gives sub-second latency, and keeps every
stream fully independent — ideal for a multi-camera grid. Frame rate,
resolution cap and JPEG quality are tunable server-side via environment
variables (`STREAM_FPS`, `STREAM_MAX_WIDTH`, `STREAM_JPEG_QUALITY`).

## Features

- ➕ Add / remove any number of RTSP streams (`rtsp://` and `rtsps://`)
- 🎛 Responsive auto-fill grid — streams play simultaneously and independently
- ⏯ Per-stream play/pause (pause halts frame delivery, resume is instant)
- 🩺 Live status badges (CONNECTING / LIVE / PAUSED / ERROR) + FPS counter
- 🧯 Graceful error handling with actionable messages:
  - invalid URL scheme, missing host
  - auth failures (401), wrong path (404), connection refused,
    DNS failures, timeouts, stalled streams (no frames for 20 s)
  - one-click **Retry / Reconnect**
- 🧹 Robust cleanup: FFmpeg processes are killed when a socket closes,
  a stream is removed, or the tab is closed — no zombie processes

## Project structure

```
rtsp-stream-viewer/
├── backend/
│   ├── core/               # Django project (settings, ASGI, URLs, CORS)
│   ├── streams/
│   │   ├── consumers.py    # WebSocket consumer (play/pause/stop protocol)
│   │   ├── ffmpeg.py       # Async FFmpeg subprocess wrapper + JPEG parser
│   │   ├── routing.py      # ws/stream/ route
│   │   └── views.py        # /api/health/, /api/demo-streams/
│   ├── manage.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── config.js       # same-origin by default, VITE_BACKEND_URL override
    │   └── components/     # AddStreamForm, StreamGrid, StreamPlayer
    ├── vite.config.js      # dev proxy → Django :8000
    └── package.json
```

## Running locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- **FFmpeg** on the backend machine (`sudo apt install ffmpeg` /
  `brew install ffmpeg`)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

### 2. Frontend

**Option A — production style (single server).** Build once; Django serves
the app at http://localhost:8000:

```bash
cd frontend
npm install
npm run build
```

**Option B — dev mode with hot reload.** Vite proxies `/api` and `/ws` to
the backend:

```bash
cd frontend
npm install
npm run dev        # open http://localhost:5173
```

### 3. Add a stream

Paste an RTSP URL, e.g.:

```
rtsp://admin:admin123@49.248.155.178:555/cam/realmonitor?channel=1&subtype=0
```

> Public test cameras are frequently offline. To generate local test
> streams, run a local RTSP server ([MediaMTX](https://github.com/bluenviron/mediamtx)) and publish a
> test pattern with FFmpeg:
>
> ```bash
> ./mediamtx &
> ffmpeg -re -f lavfi -i "testsrc2=size=1280x720:rate=25" \
>   -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
>   -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/demo1
> ```
>
> Set `DEMO_RTSP_URLS="rtsp://127.0.0.1:8554/demo1"` before starting the
> backend and the UI will show a one-click "Demo camera" button.

## Deployment

RTSP ingestion needs FFmpeg subprocesses and persistent WebSockets, so the
backend must run on a host that allows both (Render / Railway / Fly.io /
a VPS — **not** serverless platforms like Vercel functions).

### Backend → Render (one click, free tier)

The repo ships a `Dockerfile` (FFmpeg included) and a `render.yaml`
blueprint:

1. Push this repository to GitHub.
2. On [Render](https://render.com): **New → Blueprint**, select the repo,
   click **Apply**. That's it — Render builds the Docker image and starts
   the service with a health check on `/api/health/`.
3. Your app is live at `https://rtsp-stream-viewer-<hash>.onrender.com`
   (Django also serves the built frontend, so this URL is a complete,
   working demo on its own).

`DEMO_MODE=1` (default) runs a MediaMTX RTSP server *inside* the container
publishing two synthetic test cameras, so the hosted demo always has live
streams available via the "Demo camera" buttons. Set `DEMO_MODE=0` to
disable.

> Free-tier note: Render free instances sleep after ~15 min of inactivity;
> the first request after that takes ~1 min to wake up.

**Manual alternative (any Docker host / VPS):**

```bash
docker build -t rtsp-viewer .
docker run -p 8000:8000 -e DJANGO_SECRET_KEY=change-me rtsp-viewer
```

### Frontend → GitHub Pages (auto-deployed by CI)

`.github/workflows/deploy-pages.yml` builds the React app and publishes it
to GitHub Pages on every push to `main`:

1. Repo **Settings → Pages** → set **Source** to **GitHub Actions**.
2. Repo **Settings → Secrets and variables → Actions → Variables** → add
   `BACKEND_URL` = your Render URL (e.g.
   `https://rtsp-stream-viewer-xxxx.onrender.com`), no trailing slash.
3. Push to `main` (or run the workflow manually). The site appears at
   `https://<username>.github.io/<repo>/`.

The API already sends permissive CORS headers and the WebSocket route
accepts cross-origin connections, so no backend changes are needed for
split hosting.

## WebSocket protocol reference

| Direction | Message | Meaning |
|---|---|---|
| → server | `{"action":"play","url":"rtsp://…"}` | start (or resume) a stream |
| → server | `{"action":"pause"}` | pause frame delivery |
| → server | `{"action":"stop"}` | tear down the FFmpeg process |
| ← client | *binary frame* | one JPEG image |
| ← client | `{"type":"status","state":"connecting\|live\|paused\|stopped"}` | lifecycle updates |
| ← client | `{"type":"error","message":"…"}` | human-readable failure |

## Configuration (backend env vars)

| Variable | Default | Description |
|---|---|---|
| `STREAM_FPS` | `12` | output frame rate per stream |
| `STREAM_MAX_WIDTH` | `960` | downscale cap (keeps bandwidth sane) |
| `STREAM_JPEG_QUALITY` | `6` | FFmpeg `-q:v` (2 best … 31 worst) |
| `STREAM_CONNECT_TIMEOUT` | `15` | seconds to wait for the first frame |
| `DEMO_RTSP_URLS` | *(empty)* | comma-separated demo URLs shown in the UI |
| `FFMPEG_BIN` | `ffmpeg` | path to the FFmpeg binary |
