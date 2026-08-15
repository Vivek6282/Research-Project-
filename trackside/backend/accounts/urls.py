"""
Trackside — Account URL routes.

Maps authentication and user management endpoints.
No /register or /signup route exists — by design, not by oversight.
"""

from django.urls import path

from accounts.views import (
    AdminDiagnosticsView,
    AuditLogListView,
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
    # Security audit trail & diagnostics — Admin only
    path("audit-logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("diagnostics/", AdminDiagnosticsView.as_view(), name="admin-diagnostics"),
]

