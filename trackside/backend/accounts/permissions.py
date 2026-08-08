"""
Trackside — Role-based permission classes.

Every API endpoint uses one of these to enforce access server-side.
Requirement #4: no endpoint relies on the frontend to hide things — the
server independently checks request.user.role on every call.

These are always paired with DRF's IsAuthenticated (set globally in settings)
so unauthenticated requests are already rejected before role checks run.
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Allows access only to users with the 'admin' role.
    Used on: user management, device management, system settings.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsCoach(BasePermission):
    """
    Allows access only to users with the 'coach' role.
    Used on: session notes, threshold adjustments, driver roster.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "coach"
        )


class IsDriver(BasePermission):
    """
    Allows access only to users with the 'driver' role.
    Used on: driver-specific session views, personal baselines.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "driver"
        )


class IsAdminOrCoach(BasePermission):
    """
    Allows access to both admin and coach roles.
    Used on: endpoints that coaches need but admins should also be able to access
    (e.g. viewing all sessions for management purposes).
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "coach")
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: the requesting user must either own the object
    or be an admin. Used as a second check alongside queryset scoping
    to prevent IDOR (requirement #3).

    The owning field is determined by the view's `owner_field` attribute,
    defaulting to 'user' (i.e. obj.user == request.user).
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True

        # Determine which field on the object points to the owner
        owner_field = getattr(view, "owner_field", "user")
        owner = getattr(obj, owner_field, None)

        # Handle FK fields that store the user directly vs user ID
        if hasattr(owner, "pk"):
            return owner.pk == request.user.pk
        return owner == request.user.pk
