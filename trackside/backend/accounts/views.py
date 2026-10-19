"""
Trackside Accounts — Views Package Re-exports.
This file aggregates and re-exports authentication views (views_auth)
and administrative user management views (views_users) for backward compatibility.
"""

from accounts.views_auth import (
    CSRFTokenView,
    LoginView,
    LogoutView,
    MeView,
)
from accounts.views_users import (
    AdminDiagnosticsView,
    AuditLogListView,
    UserDetailView,
    UserListCreateView,
)

__all__ = [
    "CSRFTokenView",
    "LoginView",
    "LogoutView",
    "MeView",
    "UserListCreateView",
    "UserDetailView",
    "AuditLogListView",
    "AdminDiagnosticsView",
]
