"""
Trackside — Refuse oversized requests early.

The largest legitimate request is a track file import (the file limit is 5 MB). Anything over
MAX_REQUEST_BYTES is refused with 413 before it is read, so one huge upload cannot fill memory or disk.
The Caddy proxy has the same limit; this keeps it in force on hosts without that proxy (for example Render).
"""

from django.http import JsonResponse

MAX_REQUEST_BYTES = 12 * 1024 * 1024


class RequestSizeLimitMiddleware:
    """Answers 413 when the request says its body is larger than MAX_REQUEST_BYTES."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Check the declared body size, then run the request."""
        try:
            declared = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            declared = 0
        if declared > MAX_REQUEST_BYTES:
            return JsonResponse({"detail": "The request is too large."}, status=413)
        return self.get_response(request)
