"""
Trackside — Serve the built frontend (single-page app) from the backend.

Used only when FRONTEND_DIST is set (single-address hosting such as Render's free web service).
A path that is a real file is served as it is; any other path gets index.html, so deep links like
/coach reload. Hashed files under assets/ are cached for a year; everything else is re-checked.
"""

import os

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import Http404
from django.utils._os import safe_join
from django.views.decorators.http import require_safe
from django.views.static import serve


@require_safe
def spa(request, path=""):
    """Serve one file of the built frontend, or index.html for an unknown path."""
    root = settings.FRONTEND_DIST
    wanted = path or "index.html"
    try:
        found = os.path.isfile(safe_join(root, wanted))
    except SuspiciousFileOperation:
        raise Http404("Not found")
    name = wanted if found else "index.html"
    response = serve(request, name, document_root=root)
    response["Cache-Control"] = "public, max-age=31536000, immutable" if name.startswith("assets/") else "no-cache"
    return response
