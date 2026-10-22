"""
Trackside — seed_demo management command.

Prepares demo environment by creating or reusing Demo Circuit track and zones,
kart unit device with API token, and a new demo safety session.
"""

import os
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from tracks.demo_circuit_setup import PLACEHOLDER_GPS, ensure_demo_circuit
from tracks.models import Zone
from devices.models import Device
from driving_sessions.models import Session

User = get_user_model()


class Command(BaseCommand):
    help = "Seed Demo Circuit, zones, device, and a new session for demo telemetry."

    def add_arguments(self, parser):
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

        # 2. Create or reuse the built-in Track "Demo Circuit" (sprint class, locked)
        track = ensure_demo_circuit()

        # 3. Create or reuse Zones: Hairpin (1.15, hairpin), Sweeper (1.55, sweeper), Chicane (1.30, chicane)
        placeholder_gps = PLACEHOLDER_GPS

        zone_configs = [
            ("Hairpin", 1.15, Zone.CornerType.HAIRPIN),
            ("Sweeper", 1.55, Zone.CornerType.SWEEPER),
            ("Chicane", 1.30, Zone.CornerType.CHICANE),
        ]

        zones = {}
        for label, thresh, corner_type in zone_configs:
            zone, _ = Zone.objects.get_or_create(
                track=track,
                label=label,
                defaults={
                    "threshold_g": thresh,
                    "corner_type": corner_type,
                    "gps_range": placeholder_gps,
                },
            )
            updated = False
            if zone.threshold_g != thresh:
                zone.threshold_g = thresh
                updated = True
            if zone.corner_type != corner_type:
                zone.corner_type = corner_type
                updated = True
            if not zone.gps_range:
                zone.gps_range = placeholder_gps
                updated = True
            if updated:
                zone.save()
            zones[label] = zone

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
