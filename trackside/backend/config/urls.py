"""
Trackside — Django project-level URL configuration.

Routes all API traffic under /api/ and delegates to feature-specific URL modules.
Admin panel is not exposed — all admin operations go through the API.
"""

from django.conf import settings
from django.urls import path, include, re_path

from config.health import health

urlpatterns = [
    # Health check (public, no database details)
    path("api/health/", health, name="health"),
    # Authentication & user management
    path("api/auth/", include("accounts.urls")),
    # Feature modules
    path("api/tracks/", include("tracks.urls")),
    path("api/sessions/", include("driving_sessions.urls")),
    path("api/drivers/", include("drivers.urls")),
    path("api/devices/", include("devices.urls")),
    path("api/preferences/", include("preferences.urls")),
    path("api/academy/", include("academy.urls")),
    path("api/demo/", include("demo_control.urls")),
    path("api/laptop-link/", include("demo_control.laptop_urls")),
]

# Single-address hosting: the backend also serves the built website (everything except /api and /ws)
if settings.FRONTEND_DIST:
    from config.spa import spa

    urlpatterns.append(re_path(r"^(?!api/|ws/)(?P<path>.*)$", spa))
