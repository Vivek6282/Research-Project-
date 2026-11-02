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

# Sample data: when SEED_SAMPLE_DATA=true and SAMPLE_TRACK_NAME names an existing map (with corners called
# Hairpin, Sweeper and Chicane and an outline), add one finished sample (DEMO) session so the hosted site has
# something to show. Safe on every start (it does nothing when the sample already exists); a failure never
# stops the server.
if [ "${SEED_SAMPLE_DATA:-}" = "true" ]; then
    if [ -n "${SAMPLE_TRACK_NAME:-}" ]; then
        python manage.py seed_sample_data --track-name "${SAMPLE_TRACK_NAME}" || echo "seed_sample_data failed (continuing without sample data)."
    else
        echo "SEED_SAMPLE_DATA is true but SAMPLE_TRACK_NAME is not set: skipping the sample session."
    fi
fi

exec daphne -b 0.0.0.0 -p "${PORT:-10000}" config.asgi:application
