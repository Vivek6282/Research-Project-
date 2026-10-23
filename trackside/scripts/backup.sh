#!/bin/sh
# Trackside database backup: pg_dump -Fc from the db container into ./backups, newest 14 kept.
# Run from anywhere; it works in the folder that holds docker-compose.yml. No password is printed.
set -eu

cd "$(dirname "$0")/.."
# Backups hold every account and driving record: readable by the owner only
umask 077
mkdir -p backups

stamp=$(date +%Y%m%d-%H%M%S)
target="backups/trackside-$stamp.dump"
partial="$target.partial"

# The credentials come from the db container's own environment (nothing is passed on the command line)
if ! docker compose exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$partial"; then
    rm -f "$partial"
    echo "ERROR: the backup failed (is the db container running?)." >&2
    exit 1
fi
if [ ! -s "$partial" ]; then
    rm -f "$partial"
    echo "ERROR: the backup is empty." >&2
    exit 1
fi
mv "$partial" "$target"
echo "Backup written: $target"

# Keep the newest 14 backups, delete the rest
ls -1t backups/trackside-*.dump 2>/dev/null | tail -n +15 | while read -r old; do
    rm -f -- "$old"
done
