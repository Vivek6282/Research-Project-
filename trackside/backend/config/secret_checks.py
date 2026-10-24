"""
Trackside — Refuse to start production with a missing, short or placeholder SECRET_KEY.

The example .env files hold placeholder text on purpose; this check makes sure a
copied example can never become the real production key. 32 characters is the
minimum because Render's generated value is about 44 characters long.
"""

from django.core.exceptions import ImproperlyConfigured

MIN_SECRET_KEY_LENGTH = 32
MIN_DIFFERENT_CHARACTERS = 5
PLACEHOLDER_MARKERS = ("replace-me", "change-this", "change-me", "changeme", "generate-a", "dev-secret",
                       "example", "your-secret", "django-insecure", "placeholder")


def check_production_secret_key(secret_key: str) -> None:
    """Raise ImproperlyConfigured when the key is empty, too short, too repetitive or a placeholder."""
    if not secret_key:
        raise ImproperlyConfigured("Production SECRET_KEY is not set.")
    lowered = secret_key.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        raise ImproperlyConfigured("Production SECRET_KEY is still a placeholder from an example file. Generate a new one.")
    if len(secret_key) < MIN_SECRET_KEY_LENGTH or len(set(secret_key)) < MIN_DIFFERENT_CHARACTERS:
        raise ImproperlyConfigured(
            f"Production SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} random characters. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(50))"')
