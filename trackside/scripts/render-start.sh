#!/bin/sh
# Start the server on Render. Runs after backend-entrypoint.sh (settings check, database wait, migrate).
#
# First admin: Render's free plan has no shell, so if ADMIN_EMAIL and ADMIN_PASSWORD are set in the
# service's environment, seed_admin runs here (it is safe to run on every start: it only creates the
# account the first time and never changes an existing password). Remove ADMIN_PASSWORD from the
# environment after your first login. The password is never printed.
set -eu

if [ -n "${ADMIN_EMAIL:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
    python manage.py seed_admin
fi

exec daphne -b 0.0.0.0 -p "${PORT:-10000}" config.asgi:application
