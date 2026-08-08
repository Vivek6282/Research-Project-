"""
Trackside — Login rate throttle.

Requirement #9: brute-force protection on the login endpoint.
Limits anonymous login attempts to 5 per minute per IP.
Returns HTTP 429 when exceeded.
"""

from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Throttle class scoped specifically to login attempts.

    Uses the 'login' scope defined in settings.DEFAULT_THROTTLE_RATES.
    Applied only to the LoginView — not globally — so normal API usage
    isn't affected by login rate limits.

    Rate: 5 requests per minute per IP (configurable in settings).
    """

    scope = "login"
