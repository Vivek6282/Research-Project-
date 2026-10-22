"""
Trackside — seed_sample_data management command.

Adds ONE finished sample session (labelled DEMO) so a hosted site has something to show: a sample
driver on the built-in Demo Circuit with 5 laps of readings and the alerts they cause. It is safe to
run any number of times (it does nothing when the sample session already exists), never touches real
data, and creates no login: the sample driver has no usable password.

To remove it later: Admin screen, delete the "Sample Driver" (its sessions go with it).

Usage:
    python manage.py seed_sample_data
"""

import math
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from driving_sessions.alerting import process_telemetry_alerts
from driving_sessions.models import Session, Telemetry
from tracks.demo_circuit_setup import ensure_demo_circuit
from tracks.outline_gps import schematic_gps_pairs

User = get_user_model()

SAMPLE_DRIVER_NAME = "Sample Driver"
SAMPLE_KART = "Sample"
# A lap of 48 readings takes about a minute (800 m at kart pace); each lap is a little faster or slower
READING_SPACING_S = 1.2
LAP_PACE = [1.00, 0.98, 1.02, 1.04, 0.99]
# One lap of the simulator's pattern: (corner name or None for a straight, number of readings)
LAP_PATTERN = [("Hairpin", 12), (None, 6), ("Sweeper", 14), (None, 6), ("Chicane", 10)]
CORNER_SPEED_KMH = {"Hairpin": 42.0, "Sweeper": 58.0, "Chicane": 50.0}
STRAIGHT_SPEED_KMH = 88.0
# Peak g of each corner as a share of its limit, per lap: Hairpin, Sweeper, Chicane
LAP_PEAK_SHARES = [
    (0.70, 0.72, 0.75),   # lap 1: calm
    (0.80, 0.78, 0.85),   # lap 2
    (0.90, 0.76, 0.95),   # lap 3: two amber corners
    (1.04, 0.88, 0.80),   # lap 4: a red Hairpin
    (0.86, 0.80, 1.03),   # lap 5: a red Chicane
]


class Command(BaseCommand):
    help = "Add one finished sample (DEMO) session with readings and alerts. Safe to run repeatedly."

    def handle(self, *args, **options):
        track = ensure_demo_circuit()
        zones = {z.label: z for z in track.zones.filter(is_active=True)}
        driver = self.sample_driver()

        if Session.objects.filter(driver=driver, track=track, is_demo=True, kart_number=SAMPLE_KART).exists():
            self.stdout.write("Sample session already exists. Nothing to do.")
            return

        with transaction.atomic():
            session, readings = self.build_session(driver, track, zones)
            alerts = process_telemetry_alerts(session, readings)
        self.stdout.write(self.style.SUCCESS(
            f"Sample session created for '{driver.name}': {len(readings)} readings, {len(alerts)} alerts."))

    @staticmethod
    def sample_driver():
        """The sample driver (made once, with no email and no usable password, so nobody can log in as it)."""
        driver = User.objects.filter(role="driver", name=SAMPLE_DRIVER_NAME, email__isnull=True).first()
        if driver is None:
            driver = User(name=SAMPLE_DRIVER_NAME, role="driver", email=None, username=None)
            driver.set_unusable_password()
            driver.save()
        return driver

    @staticmethod
    def build_session(driver, track, zones):
        """Create the finished session and its readings (5 laps, 48 readings each, evenly spaced)."""
        rng = random.Random(2026)
        readings_per_lap = sum(count for _, count in LAP_PATTERN)
        gps_points = schematic_gps_pairs()
        total_seconds = sum(readings_per_lap * READING_SPACING_S * pace for pace in LAP_PACE)
        started = timezone.now() - timedelta(hours=2)
        session = Session.objects.create(
            driver=driver, track=track, mode=Session.Mode.PERFORMANCE, kart_number=SAMPLE_KART,
            started_at=started, ended_at=started + timedelta(seconds=total_seconds + 5), is_demo=True,
        )
        readings = []
        lap_start = 0.0
        for lap_index, shares in enumerate(LAP_PEAK_SHARES):
            peaks = dict(zip(("Hairpin", "Sweeper", "Chicane"), shares))
            number = 0
            for corner, count in LAP_PATTERN:
                for step in range(count):
                    arc = math.sin(math.pi * step / (count - 1)) if count > 1 else 1.0
                    zone = zones.get(corner) if corner else None
                    if zone is not None:
                        g = max(0.05, peaks[corner] * zone.threshold_g * arc + rng.uniform(-0.02, 0.02))
                        speed = CORNER_SPEED_KMH[corner]
                    else:
                        g = rng.uniform(0.10, 0.30)
                        speed = STRAIGHT_SPEED_KMH
                    lat, lng = gps_points[number * len(gps_points) // readings_per_lap]
                    readings.append(Telemetry(
                        session=session, zone=zone, lap_number=lap_index + 1,
                        recorded_at=started + timedelta(seconds=lap_start + number * READING_SPACING_S * LAP_PACE[lap_index]),
                        lateral_g=round(g, 2), speed_kmh=round(speed + rng.uniform(-2.0, 2.0), 1),
                        gps_lat=lat, gps_lng=lng,
                    ))
                    number += 1
            lap_start += readings_per_lap * READING_SPACING_S * LAP_PACE[lap_index]
        Telemetry.objects.bulk_create(readings)
        return session, readings
