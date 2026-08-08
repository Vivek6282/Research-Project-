"""
Trackside — Account URL routes.

Maps authentication and user management endpoints.
No /register or /signup route exists — by design, not by oversight.
"""

from django.urls import path

from accounts.views import (
    CSRFTokenView,
    LoginView,
    LogoutView,
    MeView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    # CSRF token — must be fetched before any POST/PUT/DELETE
    path("csrf/", CSRFTokenView.as_view(), name="csrf-token"),
    # Authentication
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    # User management — Admin only
    path("users/", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
]
