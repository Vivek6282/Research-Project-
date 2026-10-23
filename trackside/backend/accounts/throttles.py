"""
Trackside — Login rate throttle.

Requirement #9: brute-force protection on the login endpoint.
Limits anonymous login attempts to 5 per minute per IP, and (LoginAccountThrottle) per account.
Returns HTTP 429 when exceeded.
"""

import hashlib
import os

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Throttle class scoped specifically to login attempts.

    Uses the 'login' scope defined in settings.DEFAULT_THROTTLE_RATES.
    Applied only to the LoginView — not globally — so normal API usage
    isn't affected by login rate limits.

    Rate: 5 requests per minute per IP (configurable in settings).
    """

    scope = "login"

    def get_rate(self):
        return os.environ.get("LOGIN_THROTTLE_RATE") or super().get_rate()


class LoginAccountThrottle(SimpleRateThrottle):
    """
    Limits login attempts per ACCOUNT (the email or Driver ID typed), whatever address they come from.

    The per-address limit above depends on the server seeing each visitor's real address, which behind a
    proxy needs the right TRUSTED_PROXY_COUNT. This limit does not: guesses against one account are
    capped even when they arrive from many addresses. The key is a hash, so no identifier is stored.
    Rate: LOGIN_ACCOUNT_THROTTLE_RATE (default 10 per minute).
    """

    scope = "login_account"

    def get_rate(self):
        return os.environ.get("LOGIN_ACCOUNT_THROTTLE_RATE") or super().get_rate()

    def get_cache_key(self, request, view):
        """The throttle key for the typed identifier, or None (no limit) when none was typed."""
        data = request.data if hasattr(request.data, "get") else {}
        typed = str(data.get("identifier") or data.get("email") or "").strip().lower()
        if not typed:
            return None
        digest = hashlib.sha256(typed.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}
