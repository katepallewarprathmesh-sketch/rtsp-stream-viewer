"""Minimal CORS middleware for the small read-only API.

Only /api/ endpoints get CORS headers; the WebSocket route is unaffected
(Channels' plain URLRouter already accepts cross-origin connections).
Avoids pulling in django-cors-headers for two GET endpoints.
"""


class ApiCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response
