"""
Django settings for the RTSP Stream Viewer backend.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Where the built React app lives (frontend/dist). Served by Django so the
# whole app runs on a single origin (simplifies WebSockets + deployment).
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-key-change-me-in-production"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "daphne",  # ASGI server, must be before staticfiles
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "channels",
    "streams",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "core.middleware.ApiCorsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIST],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

DATABASES = {}  # No database needed — streams are ephemeral, per-connection.

STATIC_URL = "/static/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Streaming configuration (tunable via environment variables)
# ---------------------------------------------------------------------------
STREAM_FPS = int(os.environ.get("STREAM_FPS", "12"))          # output frame rate
STREAM_MAX_WIDTH = int(os.environ.get("STREAM_MAX_WIDTH", "960"))  # downscale cap
STREAM_JPEG_QUALITY = int(os.environ.get("STREAM_JPEG_QUALITY", "6"))  # 2(best)-31(worst)
STREAM_CONNECT_TIMEOUT = int(os.environ.get("STREAM_CONNECT_TIMEOUT", "15"))  # seconds
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")
