"""
Trackside — Health check endpoint.

GET /api/health/ answers 200 {"status": "ok"} when the database answers SELECT 1, otherwise
503 {"status": "unavailable"}. It reveals nothing else (no versions, hostnames, settings or counts).
"""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_safe


# Deliberately public (no login, no throttle): the load balancer and the container health check call it.
@require_safe
def health(request):
    """200 when the database answers a trivial query, 503 when it does not."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
