#!/bin/sh
# Trackside database restore: replaces the database contents with a named dump from ./backups.
# Usage: scripts/restore.sh backups/trackside-20261022-030000.dump
# It asks you to type RESTORE first. The backend is stopped during the restore. No password is printed.
set -eu

cd "$(dirname "$0")/.."

if [ "$#" -ne 1 ]; then
    echo "Usage: scripts/restore.sh backups/<dump file>" >&2
    exit 1
fi
dump="$1"
if [ ! -f "$dump" ] || [ ! -s "$dump" ]; then
    echo "ERROR: '$dump' is not a readable, non-empty file." >&2
    exit 1
fi

echo "This REPLACES the current database with: $dump"
printf 'Type RESTORE to continue: '
read -r answer
if [ "$answer" != "RESTORE" ]; then
    echo "Cancelled. Nothing was changed."
    exit 1
fi

# Stop the backend so nothing writes while the database is replaced; start it again afterwards
docker compose stop backend
trap 'docker compose start backend' EXIT

docker compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$dump"
echo "Restore finished. Starting the backend again."
