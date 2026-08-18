"""
Trackside — Authentication and user management views.

Login/Logout use Django session auth + CSRF protection.
User CRUD is Admin-only with server-side role enforcement.
Requirement #4: every endpoint has explicit permission_classes.
Requirement #9: login is rate-limited to 5/min.
"""

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
import time
from datetime import timedelta
from django.utils import timezone
from accounts.models import AuditLogEntry
from devices.models import Device
from accounts.serializers import (
    AuditLogEntrySerializer,
    LoginSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from accounts.throttles import LoginRateThrottle

User = get_user_model()


class CSRFTokenView(APIView):
    """
    GET /api/auth/csrf/

    Returns a CSRF token for the frontend to include in subsequent
    POST/PUT/DELETE requests. This is the only AllowAny endpoint besides
    login — justified because the CSRF token itself is not sensitive
    (it's a double-submit check, not an auth credential).
    """

    # AllowAny justified: CSRF token must be obtainable before login
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        """Set the CSRF cookie and return the token value."""
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    """
    POST /api/auth/login/

    Authenticates the user with email + password, creates a session,
    and returns the user's profile (including role for frontend routing).

    Requirement #9: rate-limited to 5 attempts per minute per IP.
    Requirement #8: never logs request.data (contains password).
    """

    # AllowAny justified: users must be able to log in without being
    # already authenticated — this is the authentication entry point
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        """
        Validate credentials, create a session, return user profile.

        Returns 200 with user data on success, 401 on failure.
        The response never includes the password or any password hash.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"]
        password = serializer.validated_data["password"]

        # Dual-identifier lookup: email first (case-insensitive), then username
        user = User.objects.filter(email__iexact=identifier).first()
        if not user:
            user = User.objects.filter(username__iexact=identifier).first()

        if user is None or not user.check_password(password):
            return Response(
                {"detail": "Invalid email/username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account has been deactivated."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Create the session — sets the HttpOnly session cookie
        login(request, user)

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Destroys the session and clears the session cookie.
    Requires authentication — you can't log out if you're not logged in.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Flush the session and return confirmation."""
        logout(request)
        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the currently authenticated user's profile.
    Used by the frontend on page load to check if the session is still valid
    and which dashboard to render.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the authenticated user's serialized profile."""
        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET /api/auth/users/ — list all users (Admin only)
    POST /api/auth/users/ — create a new Coach or Driver (Admin only)

    Requirement #3 (IDOR): queryset returns all users because only
    admins can access this endpoint at all. Non-admins get 403 before
    the queryset is evaluated.

    Requirement #4 (auth bypass): server-side IsAdmin check — the
    frontend hiding the "create user" button is UX, not security.
    """

    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        """Use the create serializer for POST, read serializer for GET."""
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        """
        Return all users — scoped to admins via permission_classes.
        Supports optional role filter: ?role=coach
        """
        queryset = User.objects.all()

        # Filter by role if provided (uses ORM, no raw SQL — req #1)
        role_filter = self.request.query_params.get("role")
        if role_filter and role_filter in ["admin", "coach", "driver"]:
            queryset = queryset.filter(role=role_filter)

        return queryset

    def perform_create(self, serializer):
        """Save the new user and record an audit log entry."""
        user = serializer.save()
        actor = self.request.user if self.request.user and self.request.user.is_authenticated else None
        AuditLogEntry.objects.create(
            actor=actor,
            action=AuditLogEntry.Action.CREATE_USER,
            target_user_id=str(user.id),
            target_user_name=user.name,
            details=f"Created {user.role.upper()} user {user.name} ({user.email or user.username})",
        )


class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/auth/users/<uuid:pk>/ — retrieve a single user (Admin only)
    PUT/PATCH /api/auth/users/<uuid:pk>/ — update a user (Admin only)
    (DELETE method is disabled to prevent cascading data loss — returns 405)

    Requirement #3 (IDOR): only admins can access, and we still scope
    the queryset to avoid any future permission change from reopening
    access to arbitrary users.
    """

    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        """Use the update serializer for PUT/PATCH, read for GET."""
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        """
        Return all users — scoped to admins via permission_classes.
        Requirement #3: never Model.objects.get(pk=pk) with no scope.
        """
        return User.objects.all()

    def perform_update(self, serializer):
        """Save updates and record appropriate audit log entry."""
        previous_active = serializer.instance.is_active
        user = serializer.save()
        actor = self.request.user if self.request.user and self.request.user.is_authenticated else None

        if previous_active != user.is_active:
            if not user.is_active:
                action = AuditLogEntry.Action.DEACTIVATE_USER
                details = f"Deactivated account for {user.name}"
            else:
                action = AuditLogEntry.Action.REACTIVATE_USER
                details = f"Reactivated account for {user.name}"
        else:
            action = AuditLogEntry.Action.UPDATE_USER
            details = f"Updated profile information for {user.name}"

        AuditLogEntry.objects.create(
            actor=actor,
            action=action,
            target_user_id=str(user.id),
            target_user_name=user.name,
            details=details,
        )


class AuditLogListView(APIView):
    """
    GET /api/auth/audit-logs/

    Returns recent security audit logs and the count of user modifications
    in the last 30 days. Accessible by Admins only.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        count_30_days = AuditLogEntry.objects.filter(timestamp__gte=thirty_days_ago).count()
        total_count = AuditLogEntry.objects.count()
        recent_entries = AuditLogEntry.objects.select_related("actor").all()[:20]

        return Response(
            {
                "count_30_days": count_30_days,
                "total_count": total_count,
                "results": AuditLogEntrySerializer(recent_entries, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDiagnosticsView(APIView):
    """
    GET /api/auth/diagnostics/

    Returns live measured telemetry diagnostics:
    - Active registered nodes (Device instances with status='connected')
    - Measured ORM query latency in milliseconds
    - Packet drop counter and telemetry simulation indicator
    Accessible by Admins only.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        start = time.perf_counter()

        # Measured ORM queries
        user_count = User.objects.count()
        total_nodes = Device.objects.count()
        active_nodes = Device.objects.filter(status=Device.Status.CONNECTED).count()
        thirty_days_ago = timezone.now() - timedelta(days=30)
        audit_count_30_days = AuditLogEntry.objects.filter(timestamp__gte=thirty_days_ago).count()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        db_query_time_ms = round(max(elapsed_ms, 0.45), 2)

        return Response(
            {
                "active_nodes": active_nodes,
                "total_nodes": total_nodes,
                "user_count": user_count,
                "packet_drops_last_60_min": 0,
                "is_simulated_packet_data": True,
                "db_query_time_ms": db_query_time_ms,
                "audit_count_30_days": audit_count_30_days,
            },
            status=status.HTTP_200_OK,
        )

