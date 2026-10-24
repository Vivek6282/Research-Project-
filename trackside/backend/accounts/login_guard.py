"""
Trackside Accounts — Sign-in lockout and security logging.

Lockout: after MAX_FAILED_SIGN_INS wrong passwords within LOCKOUT_WINDOW_S,
sign-in is refused for LOCKOUT_WINDOW_S, even with the right password. The
counter belongs to the account when the typed text matches one (so its email,
username and driver ID share one counter) and to the typed text otherwise; the
answer is the same either way, so it cannot reveal which accounts exist. Keys
are hashes, so no identifier is stored.

Logging: successes, failures, lockouts and sign-outs go to the
"trackside.security" logger with the account id (never the password, the
typed text of an unknown identifier, or any session key).
"""

import hashlib
import logging
import os

from django.core.cache import cache
from rest_framework.throttling import BaseThrottle

security_log = logging.getLogger("trackside.security")

MAX_FAILED_SIGN_INS = int(os.environ.get("LOGIN_LOCKOUT_ATTEMPTS", "10"))
LOCKOUT_WINDOW_S = int(os.environ.get("LOGIN_LOCKOUT_SECONDS", str(15 * 60)))
LOCKED_MESSAGE = "Too many failed sign-in attempts. Try again in 15 minutes."


def lockout_key(identifier: str, user=None) -> str:
    """Cache key: the matched account's id, or the typed text (case-insensitive), hashed."""
    source = f"user:{user.pk}" if user is not None else f"typed:{identifier.strip().lower()}"
    return "login-failures:" + hashlib.sha256(source.encode("utf-8")).hexdigest()


def is_locked(identifier: str, user=None) -> bool:
    """True when this account (or typed text) has reached the failure limit inside the window."""
    return cache.get(lockout_key(identifier, user), 0) >= MAX_FAILED_SIGN_INS


def record_failure(identifier: str, user=None) -> int:
    """Count one more failure (the window starts at the first failure) and return the new count."""
    key = lockout_key(identifier, user)
    if cache.add(key, 1, LOCKOUT_WINDOW_S):
        return 1
    try:
        return cache.incr(key)
    except ValueError:   # expired between add and incr
        cache.set(key, 1, LOCKOUT_WINDOW_S)
        return 1


def clear_failures(identifier: str, user=None) -> None:
    """Forget the failures after a successful sign-in."""
    cache.delete(lockout_key(identifier, user))


def client_address(request) -> str:
    """The caller's address as the rate limits see it (honours TRUSTED_PROXY_COUNT)."""
    return BaseThrottle().get_ident(request) or "unknown"


def log_event(event: str, request, user=None) -> None:
    """Write one sign-in event: what happened, from where, and for which account id (if any)."""
    account = f"user={user.pk} role={user.role}" if user is not None else "user=unknown"
    security_log.info("auth.%s %s ip=%s", event, account, client_address(request))
