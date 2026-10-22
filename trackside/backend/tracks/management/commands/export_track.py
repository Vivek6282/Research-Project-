"""
Trackside — export_track management command (SIM-1).

Usage: python manage.py export_track <track_id> --out <path>
Writes the JSON profile the virtual lap simulator reads with --track-file.
"""

import json
import os
import uuid

from django.core.management.base import BaseCommand, CommandError

from tracks.models import Track
from tracks.track_profile import ProfileError, build_track_profile


class Command(BaseCommand):
    """Write one track's simulator profile to a file."""

    help = "Export an active custom track as a simulator profile (JSON)."

    def add_arguments(self, parser):
        """Declare the track id and --out path."""
        parser.add_argument("track_id", help="UUID of the track")
        parser.add_argument("--out", required=True, help="Path of the JSON file to write")

    def handle(self, *args, **options):
        """Check the track, build the profile and write it."""
        try:
            track_uuid = uuid.UUID(str(options["track_id"]))
        except ValueError:
            raise CommandError("track_id must be a UUID.")
        track = Track.objects.filter(pk=track_uuid).first()
        if track is None:
            raise CommandError("No track with that id.")
        try:
            profile = build_track_profile(track)
        except ProfileError as error:
            raise CommandError(str(error))
        out_path = os.path.abspath(options["out"])
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(profile, handle, separators=(",", ":"))
        for label in profile["skipped_corners"]:
            self.stderr.write(f"Skipped corner '{label}': it could not be placed on the outline.")
        self.stdout.write(
            f"Wrote {out_path}: {len(profile['outline'])} outline points, {len(profile['corners'])} corners, "
            f"{profile['length_m']} m."
        )
