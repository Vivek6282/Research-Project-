"""
Trackside — Django settings.

All secrets loaded from environment variables (requirement #10).
Security defaults are production-safe; development overrides come from .env only.
"""

import os
import re
from pathlib import Path
import environ

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# ENVIRONMENT — django-environ reads .env from the backend root
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    DJANGO_ENV=(str, "production"),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------------------
# CORE SETTINGS
# ---------------------------------------------------------------------------
# Requirement #10: SECRET_KEY from env, never hardcoded
SECRET_KEY = env("SECRET_KEY", default="")

# Safe default is False — only True if .env says so
DEBUG = env.bool("DEBUG", default=False)

DJANGO_ENV = env("DJANGO_ENV", default="development")

if DJANGO_ENV == "production":
    if not SECRET_KEY or "replace-me" in SECRET_KEY.lower():
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("Production SECRET_KEY cannot be empty or contain placeholder 'replace-me'.")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])

# Render sets this to the service's public host name (for example trackside.onrender.com):
# it is allowed and trusted automatically, so nothing has to be typed in by hand.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Hosts the page may load map pictures (tiles) from. The default is OpenStreetMap's. For satellite or another
# provider, list its host here (comma separated, https only) and set VITE_MAP_TILE_URL when building the frontend.
MAP_TILE_HOSTS = env.list("MAP_TILE_HOSTS", default=["https://tile.openstreetmap.org"])
if any(not re.fullmatch(r"https://(\*\.)?[A-Za-z0-9.-]+(:[0-9]{1,5})?", host) for host in MAP_TILE_HOSTS):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("MAP_TILE_HOSTS must be https hosts such as https://tile.openstreetmap.org (no paths, spaces or other text).")

# Folder with the built frontend. When set, the backend serves the website itself (single-address hosting).
FRONTEND_DIST = env("FRONTEND_DIST", default="")

# ---------------------------------------------------------------------------
# INSTALLED APPS — feature-organized modules
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "daphne",
    "channels",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Trackside feature apps
    "accounts",
    "tracks",
    "driving_sessions",
    "drivers",
    "devices",
    "preferences",
    "demo_control",
    "academy",
]


ASGI_APPLICATION = "config.asgi.application"

# In-memory channel layer for local dev & testing
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    # Answers /api/health/ first (see config/health.py)
    "config.health.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Private API answers are never stored by browsers, proxies or the service worker (config/no_store.py)
    "config.no_store.NoStoreApiMiddleware",
    # Refuse oversized requests early (config/limits.py)
    "config.limits.RequestSizeLimitMiddleware",
    # CORS must come before CommonMiddleware
    "corsheaders.middleware.CorsMiddleware",
    # One session cookie per role area, so two roles can be signed in at once in one browser (config/area_session.py)
    "config.area_session.AreaSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CSRF protection — non-negotiable
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# DATABASE — ORM only, no raw SQL (requirement #1)
# Supports both SQLite (development) and PostgreSQL (production).
# Reads DATABASE_URL if present, otherwise DB_ENGINE.
# Refuses SQLite in production (S9).
# ---------------------------------------------------------------------------
DATABASE_URL = env("DATABASE_URL", default="")
DB_ENGINE = env("DB_ENGINE", default="sqlite3")

if DATABASE_URL:
    DATABASES = {"default": env.db("DATABASE_URL")}
elif DB_ENGINE == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="trackside_db"),
            "USER": env("DB_USER", default="trackside_user"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }
else:
    # SQLite for local development — switch to PostgreSQL for production
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if DJANGO_ENV == "production" and DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("SQLite database is not permitted when DJANGO_ENV=production.")

# ---------------------------------------------------------------------------
# CHANNELS & CHANNEL LAYERS
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

# UUID primary keys are set explicitly on each model's id field.
# DEFAULT_AUTO_FIELD must subclass AutoField — UUIDField doesn't.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# CUSTOM USER MODEL
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# DJANGO REST FRAMEWORK
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # Requirement #4: every endpoint is authenticated by default — nothing
    # is publicly accessible unless explicitly marked AllowAny with a comment
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Session authentication for browser users (device tokens only allowed on specific views)
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Requirement #9: login rate limiting & S4 device telemetry rate limiting
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "login": env("LOGIN_THROTTLE_RATE", default="5/min"),
        # Per account typed, whatever the address (see accounts/throttles.py)
        "login_account": env("LOGIN_ACCOUNT_THROTTLE_RATE", default="10/min"),
        "device_telemetry": env("DEVICE_TELEMETRY_THROTTLE_RATE", default="600/min"),
        # C2: at most 10 track-file import previews per hour per user
        "track_import": "10/hour",
        "track_import_confirm": "10/hour",
        # Drawing a track on the map: cheap to check, so a looser limit than file imports
        "track_draw": "60/hour",
        # Phase 2.0: device events (crash, lost contact, heartbeat, ...) per sending device or driver
        "device_events": env("DEVICE_EVENTS_THROTTLE_RATE", default="120/min"),
    },
    # JSON only — no browsable API in production
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Pagination defaults
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# Rate limits identify a client by its address. Behind the reverse proxy every request arrives
# from the proxy, so DRF must read the real client address from X-Forwarded-For. TRUSTED_PROXY_COUNT
# is how many proxies sit in front (1 = Caddy). The proxy must APPEND the real client address and
# must REPLACE (not trust) any X-Forwarded-For the client sent, or the limit can be dodged.
# 0 leaves DRF reading the connection address, as in development.
TRUSTED_PROXY_COUNT = env.int("TRUSTED_PROXY_COUNT", default=1 if DJANGO_ENV == "production" else 0)
if TRUSTED_PROXY_COUNT < 0:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("TRUSTED_PROXY_COUNT must be 0 or more.")
if TRUSTED_PROXY_COUNT >= 1:
    REST_FRAMEWORK["NUM_PROXIES"] = TRUSTED_PROXY_COUNT

# In development, allow the browsable API for convenience
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

# ---------------------------------------------------------------------------
# SESSION & COOKIE SECURITY
# ---------------------------------------------------------------------------
# Send only the site's address (never a path) to other sites, so map tile servers can see who is asking
# (OpenStreetMap's rules require a Referer) without learning which page of the app is open.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Requirement #5: JSON session serializer — no pickle ever
SESSION_SERIALIZER = "django.contrib.sessions.serializers.JSONSerializer"

# Session cookie is HttpOnly — JavaScript cannot read it (defense in depth)
SESSION_COOKIE_HTTPONLY = True

# CSRF cookie is NOT HttpOnly — frontend needs to read it to send in headers
CSRF_COOKIE_HTTPONLY = False

# Cookie SameSite policy for local dev & production cross-origin session handling
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Requirement #8: Django's default hasher is PBKDF2-SHA256 — don't override
# PASSWORD_HASHERS to anything weaker. Left as default intentionally.

# ---------------------------------------------------------------------------
# PRODUCTION SECURITY HARDENING
# ---------------------------------------------------------------------------
if DJANGO_ENV == "production":
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    # Behind the HTTPS reverse proxy (Caddy): trust its X-Forwarded-Proto so requests are not
    # redirected to https forever. The proxy must set this header itself (never the client).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = False
    # The container health check calls this path over plain http inside the compose network
    SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# ---------------------------------------------------------------------------
# CORS & CSRF — dev origins merged with configured environment origins
# ---------------------------------------------------------------------------
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]


def clean_origin_list(name):
    """The comma-separated origins in an environment variable, without blanks."""
    return [origin.strip() for origin in env.list(name, default=[]) if origin.strip()]


def without_duplicates(items):
    """The items in their original order, each one once."""
    return list(dict.fromkeys(items))


# CORS_ALLOWED_ORIGINS is the name to use; the older singular CORS_ALLOWED_ORIGIN is still accepted
env_cors_origins = clean_origin_list("CORS_ALLOWED_ORIGINS") + clean_origin_list("CORS_ALLOWED_ORIGIN")
if RENDER_EXTERNAL_HOSTNAME:
    env_cors_origins.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
env_csrf_origins = clean_origin_list("CSRF_TRUSTED_ORIGINS")

if DJANGO_ENV == "production":
    from django.core.exceptions import ImproperlyConfigured
    for origin in env_cors_origins + env_csrf_origins:
        if not origin.startswith("https://"):
            raise ImproperlyConfigured(
                f"Origin '{origin}' must start with https:// when DJANGO_ENV=production "
                "(check CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS)."
            )

# The local development addresses are trusted only in development; a production server trusts only its own origins
CORS_ALLOWED_ORIGINS = without_duplicates((DEV_ORIGINS if DJANGO_ENV != "production" else []) + env_cors_origins)
CORS_ALLOW_CREDENTIALS = True

# CSRF trusted origins: all the CORS origins plus the optional CSRF_TRUSTED_ORIGINS list
CSRF_TRUSTED_ORIGINS = without_duplicates(CORS_ALLOWED_ORIGINS + env_csrf_origins)

# ---------------------------------------------------------------------------
# INTERNATIONALIZATION & HARDWARE WINDOWS
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEVICE_ONLINE_WINDOW_SECONDS = env.int("DEVICE_ONLINE_WINDOW_SECONDS", default=30)


# ---------------------------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Live driver telemetry freshness window (in seconds)
DRIVER_LIVE_WINDOW_SECONDS = env.int("DRIVER_LIVE_WINDOW_SECONDS", default=30)
