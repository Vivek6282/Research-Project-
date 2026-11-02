"""
Trackside — seed_demo management command.

Prepares a demo environment on an existing map (--track-name; it needs corners called Hairpin,
Sweeper and Chicane): kart unit device with API token, and a new demo safety session.
"""

import os
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from driving_sessions.management.commands._demo_map import add_track_argument, find_map
from devices.models import Device
from driving_sessions.models import Session

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a device and a new session on an existing map for demo telemetry."

    def add_arguments(self, parser):
        add_track_argument(parser)
        parser.add_argument(
            "--driver-email",
            required=True,
            help="Email of an existing driver",
        )
        parser.add_argument(
            "--new-token",
            action="store_true",
            default=False,
            help="Force regeneration of device API token",
        )

    def handle(self, *args, **options):
        # 1. Refuse in production
        env_val = os.environ.get("DJANGO_ENV", "").lower()
        settings_val = getattr(settings, "DJANGO_ENV", "").lower()
        if env_val == "production" or settings_val == "production":
            raise CommandError("seed_demo cannot be run in production environment.")

        driver_email = options["driver_email"]
        try:
            driver = User.objects.get(email=driver_email)
        except User.DoesNotExist:
            raise CommandError(f"Driver with email '{driver_email}' does not exist.")

        # 2. Use the chosen map and its three simulator corners (nothing on the map is created or changed)
        track, zones = find_map(options["track_name"])

        # 4. Create or reuse Device (kart_unit) assigned to driver
        device, _ = Device.objects.get_or_create(
            device_type=Device.DeviceType.KART_UNIT,
            assigned_to=driver,
        )

        raw_token = None
        if not device.api_key_hash or options.get("new_token"):
            raw_token = device.set_api_key()
            device.save()

        # 5. Create a NEW Session for that driver on that track
        session = Session.objects.create(
            driver=driver,
            track=track,
            mode=Session.Mode.SAFETY,
            kart_number="demo",
            started_at=timezone.now(),
        )

        # 6. Print lines ready to paste into demo/.env (do not write the file)
        self.stdout.write("BACKEND_URL=http://localhost:8000")
        self.stdout.write(f"SESSION_ID={session.id}")
        if raw_token:
            self.stdout.write(f"DEVICE_TOKEN={raw_token}")
        demo_zones_json = json.dumps(
            {
                "Hairpin": str(zones["Hairpin"].id),
                "Sweeper": str(zones["Sweeper"].id),
                "Chicane": str(zones["Chicane"].id),
            },
            separators=(",", ":"),
        )
        self.stdout.write(f"DEMO_ZONES={demo_zones_json}")
