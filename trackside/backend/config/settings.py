"""
Trackside — Django settings.

All secrets loaded from environment variables (requirement #10).
Security defaults are production-safe; development overrides come from .env only.
"""

import os
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
SECRET_KEY = env("SECRET_KEY")

# Safe default is False — only True if .env says so
DEBUG = env("DEBUG")

DJANGO_ENV = env("DJANGO_ENV")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

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
    "django.middleware.security.SecurityMiddleware",
    # CORS must come before CommonMiddleware
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
# Set DB_ENGINE=postgresql in .env to use PostgreSQL.
# ---------------------------------------------------------------------------
DB_ENGINE = env("DB_ENGINE", default="sqlite3")

if DB_ENGINE == "postgresql":
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
    # Session authentication for browser users + DeviceTokenAuthentication for physical IoT devices
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "devices.authentication.DeviceTokenAuthentication",
    ],
    # Requirement #9: login rate limiting
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
    },
    # JSON only — no browsable API in production
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Pagination defaults
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# In development, allow the browsable API for convenience
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

# ---------------------------------------------------------------------------
# SESSION & COOKIE SECURITY
# ---------------------------------------------------------------------------
# Requirement #5: JSON session serializer — no pickle ever
SESSION_SERIALIZER = "django.contrib.sessions.serializers.JSONSerializer"

# Session cookie is HttpOnly — JavaScript cannot read it (defense in depth)
SESSION_COOKIE_HTTPONLY = True

# CSRF cookie is NOT HttpOnly — frontend needs to read it to send in headers
CSRF_COOKIE_HTTPONLY = False

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

# ---------------------------------------------------------------------------
# CORS — exact dev origin only, never CORS_ALLOW_ALL_ORIGINS with credentials
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGIN",
    default=["http://localhost:5173"],
)
CORS_ALLOW_CREDENTIALS = True

# CSRF trusted origins must match the frontend origin
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ---------------------------------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC FILES & MOCK FLAGS
# ---------------------------------------------------------------------------
STATIC_URL = "static/"

# Set to False in production or when testing real GPS track survey uploads
TRACKSIDE_USE_MOCK_SURVEY_DATA = env.bool("TRACKSIDE_USE_MOCK_SURVEY_DATA", default=True)
STATIC_ROOT = BASE_DIR / "staticfiles"
