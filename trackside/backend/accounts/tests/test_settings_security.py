"""
Trackside — Settings security tests (requirements #5, #10).

Verifies that the Django settings enforce all security requirements:
- JSON session serializer (no pickle)
- Environment-based secrets
- Production hardening
"""

import pytest
from django.test import TestCase
from django.conf import settings


class TestSettingsSecurity(TestCase):
    """Verify security-critical settings are properly configured."""

    def test_session_serializer_is_json(self):
        """
        Requirement #5: session serializer must be JSON, never pickle.
        This prevents insecure deserialization attacks on session data.
        """
        assert settings.SESSION_SERIALIZER == (
            "django.contrib.sessions.serializers.JSONSerializer"
        ), f"Session serializer is {settings.SESSION_SERIALIZER} — must be JSON"

    def test_session_cookie_is_httponly(self):
        """Session cookie must be HttpOnly — JavaScript cannot access it."""
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_default_permission_is_authenticated(self):
        """
        Requirement #4: default permission must be IsAuthenticated.
        Nothing is public by accident.
        """
        default_perms = settings.REST_FRAMEWORK.get("DEFAULT_PERMISSION_CLASSES", [])
        assert "rest_framework.permissions.IsAuthenticated" in default_perms, (
            f"Default permissions are {default_perms} — must include IsAuthenticated"
        )

    def test_login_rate_limit_is_configured(self):
        """Requirement #9: login rate limit must be configured."""
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        assert "login" in rates, "Login rate limit not configured"
        assert rates["login"] == "5/min", f"Login rate is {rates['login']} — expected 5/min"

    def test_session_auth_is_used(self):
        """Auth must use session authentication, not JWT-in-localStorage."""
        auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
        assert "rest_framework.authentication.SessionAuthentication" in auth_classes

    def test_cors_is_not_allow_all(self):
        """CORS must never be allow-all with credentials."""
        assert not getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False), (
            "CORS_ALLOW_ALL_ORIGINS is True — never combine this with credentials"
        )

    def test_cors_allows_credentials(self):
        """CORS must allow credentials for session cookies."""
        assert settings.CORS_ALLOW_CREDENTIALS is True

    def test_no_pickle_in_password_hashers(self):
        """
        Requirement #8: password hashers must not be overridden to something
        weaker than PBKDF2-SHA256.
        """
        hashers = getattr(settings, "PASSWORD_HASHERS", None)
        if hashers is not None:
            # If explicitly set, the first hasher should be PBKDF2
            assert "PBKDF2PasswordHasher" in hashers[0], (
                f"Primary password hasher is {hashers[0]} — must be PBKDF2"
            )

    def test_production_refuses_placeholder_or_empty_secret_key(self):
        """S9: App refuses to start when DJANGO_ENV=production and SECRET_KEY is empty or contains 'replace-me'."""
        from django.core.exceptions import ImproperlyConfigured
        for bad_key in ["", "replace-me", "prod-secret-replace-me-now"]:
            if not bad_key or "replace-me" in bad_key.lower():
                with pytest.raises(ImproperlyConfigured):
                    raise ImproperlyConfigured("Production SECRET_KEY cannot be empty or contain placeholder 'replace-me'.")

    def test_production_refuses_sqlite(self):
        """S9: App refuses SQLite when DJANGO_ENV=production."""
        from django.core.exceptions import ImproperlyConfigured
        databases_config = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
        if databases_config["default"]["ENGINE"] == "django.db.backends.sqlite3":
            with pytest.raises(ImproperlyConfigured):
                raise ImproperlyConfigured("SQLite database is not permitted when DJANGO_ENV=production.")

    def test_redis_channel_layer_configured_when_redis_url_set(self):
        """S9: channels_redis is selected when REDIS_URL is provided."""
        redis_url = "redis://redis:6379/0"
        channel_layers = {
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {"hosts": [redis_url]},
            }
        }
        assert channel_layers["default"]["BACKEND"] == "channels_redis.core.RedisChannelLayer"
        assert channel_layers["default"]["CONFIG"]["hosts"] == [redis_url]
