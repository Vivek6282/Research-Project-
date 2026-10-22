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

# Sample data: when SEED_SAMPLE_DATA=true, add one finished sample (DEMO) session so the hosted site has
# something to show. Safe on every start (it does nothing when the sample already exists); a failure never
# stops the server.
if [ "${SEED_SAMPLE_DATA:-}" = "true" ]; then
    python manage.py seed_sample_data || echo "seed_sample_data failed (continuing without sample data)."
fi

exec daphne -b 0.0.0.0 -p "${PORT:-10000}" config.asgi:application
