"""
Trackside Accounts — Authentication Views.
This module provides session-based authentication endpoints:
CSRF token retrieval, user login with rate limiting, user logout, and current session profile check.
"""

from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.login_guard import LOCKED_MESSAGE, MAX_FAILED_SIGN_INS, clear_failures, is_locked, log_event, record_failure
from accounts.models import AuditLogEntry
from accounts.serializers import LoginSerializer, UserSerializer
from config.area_session import AREA_HEADER, AUTO, clean_area, cookie_name_for
from accounts.throttles import LoginAccountThrottle, LoginRateThrottle

User = get_user_model()

# A real password hash of a throw-away text, used only to spend the same time when no account matches
DUMMY_PASSWORD_HASH = make_password("not-a-real-password-just-for-timing")


class CSRFTokenView(APIView):
    """
    GET /api/auth/csrf/

    Returns a CSRF token for the frontend client to include in subsequent state-modifying requests.
    Security: AllowAny is explicitly permitted because the CSRF token is a double-submit token,
    not a secret authentication credential.
    """

    # AllowAny justified: CSRF token must be obtainable before login
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        """
        Sets the CSRF cookie on the HTTP response and returns the token in JSON.
        Input: HTTP GET request.
        Output: JSON object containing csrfToken string.
        """
        token_value = get_token(request)
        return Response({"csrfToken": token_value})


class LoginView(APIView):
    """
    POST /api/auth/login/

    Authenticates user credentials using email or username, creates a Django session,
    and returns the authenticated user profile.
    Security:
    - Rate-limited to 5 attempts per minute per IP (LoginRateThrottle) and 10 per minute per account
      (LoginAccountThrottle) to prevent brute-force attacks.
    - Credentials are never logged in plaintext.
    - Deactivated accounts are rejected.
    """

    # AllowAny justified: users must be able to log in without being
    # already authenticated — this is the authentication entry point
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle, LoginAccountThrottle]

    def post(self, request):
        """
        Validates login credentials, starts a new session, and returns user details.
        Input: JSON with 'identifier' (email or username) and 'password'.
        Output: Serialized User object on success, or 401 Unauthorized with error detail.
        """
        login_serializer = LoginSerializer(data=request.data)
        login_serializer.is_valid(raise_exception=True)

        user_identifier = login_serializer.validated_data["identifier"].strip()
        raw_password = login_serializer.validated_data["password"]

        # Look the person up by email, then the long username (TRK-DRV-...), then the short driver ID (D12345)
        matched_user = User.objects.filter(email__iexact=user_identifier).first()
        if not matched_user:
            matched_user = User.objects.filter(username__iexact=user_identifier).first()
        if not matched_user:
            matched_user = User.objects.filter(driver_code__iexact=user_identifier).first()

        # Locked after too many wrong passwords: the same answer whether or not the account exists
        if is_locked(user_identifier, matched_user):
            log_event("login_locked", request, matched_user)
            return Response({"detail": LOCKED_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Do the same password work whether or not the account exists, so the answer time does not reveal
        # which accounts exist (a missing account is checked against a fixed dummy hash).
        if matched_user is None:
            check_password(raw_password, DUMMY_PASSWORD_HASH)
            password_ok = False
        else:
            password_ok = matched_user.check_password(raw_password)

        if not password_ok:
            failures = record_failure(user_identifier, matched_user)
            log_event("login_failed", request, matched_user)
            if matched_user is not None and failures == MAX_FAILED_SIGN_INS:
                AuditLogEntry.objects.create(
                    actor=None, action=AuditLogEntry.Action.SIGN_IN_LOCKED, target_user_id=str(matched_user.id),
                    target_user_name=matched_user.name,
                    details=f"Sign-in locked for 15 minutes after {failures} wrong passwords")
            return Response(
                {"detail": "Invalid email/username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not matched_user.is_active:
            return Response(
                {"detail": "This account has been deactivated."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Which session cookie this sign-in goes into: the account's own role area ("auto"), or the old single cookie
        # when the caller names no area. A caller that names another area than the account's own is refused.
        area_header = request.META.get(AREA_HEADER)
        if area_header == AUTO:
            request._request.session_cookie_name = cookie_name_for(matched_user.role)
        elif clean_area(area_header) and clean_area(area_header) != matched_user.role:
            return Response(
                {"detail": "This account cannot sign in here. Use the sign-in page."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create the session — sets the HttpOnly session cookie (Django gives it a new key, so no fixation)
        login(request, matched_user)
        clear_failures(user_identifier, matched_user)
        log_event("login_ok", request, matched_user)

        serialized_user = UserSerializer(matched_user).data
        return Response(serialized_user, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Terminates the current user session and clears the session cookie.
    Security: Requires authentication so only active session owners can terminate their session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Flushes the current session store and clears the session cookie.
        Input: Authenticated HTTP POST request.
        Output: Confirmation message with 200 OK.
        """
        log_event("logout", request, request.user)
        logout(request)
        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the authenticated user's profile to verify session validity on client load.
    Security: Requires an active, authenticated session.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieves the profile of the currently logged-in user.
        Input: Authenticated HTTP GET request with session cookie.
        Output: Serialized User profile JSON.
        """
        serialized_profile = UserSerializer(request.user).data
        return Response(serialized_profile, status=status.HTTP_200_OK)
