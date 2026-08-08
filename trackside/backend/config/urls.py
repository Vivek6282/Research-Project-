"""
Trackside — Django project-level URL configuration.

Routes all API traffic under /api/ and delegates to feature-specific URL modules.
Admin panel is not exposed — all admin operations go through the API.
"""

from django.urls import path, include

urlpatterns = [
    # Authentication & user management
    path("api/auth/", include("accounts.urls")),
    # Feature modules
    path("api/tracks/", include("tracks.urls")),
    path("api/sessions/", include("driving_sessions.urls")),
    path("api/drivers/", include("drivers.urls")),
    path("api/devices/", include("devices.urls")),
    path("api/preferences/", include("preferences.urls")),
]
