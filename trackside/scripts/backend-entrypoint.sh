#!/bin/sh
# Trackside backend start-up: check the settings, wait for the database, migrate, then run the server.
# It never creates a user or a password (the first admin is made by hand with seed_admin).
set -eu

# In production DEBUG must be False
if [ "${DJANGO_ENV:-}" = "production" ]; then
    debug_value=$(printf '%s' "${DEBUG:-}" | tr '[:upper:]' '[:lower:]')
    if [ "$debug_value" != "false" ]; then
        echo "ERROR: DJANGO_ENV=production requires DEBUG=False. Refusing to start." >&2
        exit 1
    fi
fi

# Wait until the database accepts connections (at most 60 seconds)
python - <<'PY'
import os, sys, time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection

deadline = time.monotonic() + 60
while True:
    try:
        connection.ensure_connection()
        break
    except Exception:
        connection.close()
        if time.monotonic() >= deadline:
            print("ERROR: the database did not accept connections within 60 seconds.", file=sys.stderr)
            sys.exit(1)
        time.sleep(2)
print("Database is ready.")
PY

python manage.py migrate --noinput

exec "$@"
