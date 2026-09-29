import os

from django.http import JsonResponse


def health(_request):
    return JsonResponse({"status": "ok"})


def demo_streams(_request):
    """
    Return demo RTSP URLs the backend can reach, so the UI can offer
    one-click test streams. Configure via DEMO_RTSP_URLS (comma-separated).
    """
    raw = os.environ.get("DEMO_RTSP_URLS", "")
    urls = [u.strip() for u in raw.split(",") if u.strip()]
    return JsonResponse({"streams": urls})
