"""
Trackside — Logging set-up.

Everything goes to the console (Render and Docker collect it). The
"trackside.security" logger records sign-in events at INFO level; other
loggers keep Django's usual WARNING level.
"""

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "trackside.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
