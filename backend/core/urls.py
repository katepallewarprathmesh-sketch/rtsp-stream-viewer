from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.urls import path, re_path
from django.views.static import serve

from streams.views import demo_streams, health


def index(_request):
    index_file = Path(settings.FRONTEND_DIST) / "index.html"
    if not index_file.exists():
        return JsonResponse(
            {
                "detail": "Frontend build not found. Run `npm run build` inside "
                "the frontend/ directory first."
            },
            status=503,
        )
    return FileResponse(open(index_file, "rb"), content_type="text/html")


def spa_or_404(request, resource=""):
    """Serve real files from the frontend build, else fall back to the SPA."""
    candidate = Path(settings.FRONTEND_DIST) / resource
    if resource and candidate.is_file():
        return serve(request, resource, document_root=settings.FRONTEND_DIST)
    raise Http404


urlpatterns = [
    path("api/health/", health),
    path("api/demo-streams/", demo_streams),
    path("", index),
    re_path(
        r"^assets/(?P<path>.*)$",
        serve,
        {"document_root": Path(settings.FRONTEND_DIST) / "assets"},
    ),
    re_path(r"^(?P<resource>favicon\.svg|favicon\.ico)$", spa_or_404),
]
