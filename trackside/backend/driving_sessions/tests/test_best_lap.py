"""
Trackside — Tests for best_lap computation and lap aggregation in SessionSerializer.
"""

from datetime import datetime, timezone, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tracks.models import Track
from driving_sessions.models import Session, Telemetry
from driving_sessions.serializers import SessionSerializer

User = get_user_model()


class TestBestLap(APITestCase):

    def setUp(self):
        super().setUp()
        self.driver = User.objects.create_user(
            email="lap_driver@trackside.local",
            name="Lap Driver",
            role="driver",
            password="DriverPassword123!",
        )
        self.track = Track.objects.create(name="Lap Circuit", kart_class=Track.KartClass.SPRINT)
        self.now = datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)

        self.session = Session.objects.create(
            driver=self.driver,
            track=self.track,
            mode=Session.Mode.SAFETY,
            kart_number="15",
            started_at=self.now,
            ended_at=None,
        )

    def test_no_telemetry_gives_null_best_lap_and_null_laps(self):
        """When no telemetry readings exist, best_lap and laps are both null."""
        data = SessionSerializer(self.session).data
        self.assertIsNone(data["best_lap"])
        self.assertIsNone(data["laps"])

    def test_best_lap_two_laps_known_timestamps_in_progress_ignored(self):
        """
        - Two completed laps with known timestamps: shortest completed lap is chosen.
        - An in-progress lap (highest lap_number while ended_at is null) is ignored even if faster.
        """
        base_time = self.now

        # Lap 1: 5 readings spanning exactly 65.432 seconds (1:05.432)
        for i in range(5):
            Telemetry.objects.create(
                session=self.session,
                recorded_at=base_time + timedelta(seconds=i * (65.432 / 4)),
                lateral_g=0.9,
                speed_kmh=60.0,
                gps_lat=12.9716,
                gps_lng=77.5946,
                lap_number=1,
            )

        # Lap 2: 5 readings spanning exactly 48.320 seconds (0:48.320)
        lap2_start = base_time + timedelta(seconds=70)
        for i in range(5):
            Telemetry.objects.create(
                session=self.session,
                recorded_at=lap2_start + timedelta(seconds=i * (48.320 / 4)),
                lateral_g=1.0,
                speed_kmh=70.0,
                gps_lat=12.9716,
                gps_lng=77.5946,
                lap_number=2,
            )

        # Lap 3: 5 readings spanning 40.000 seconds (0:40.000), but highest lap while ended_at is None
        lap3_start = base_time + timedelta(seconds=120)
        for i in range(5):
            Telemetry.objects.create(
                session=self.session,
                recorded_at=lap3_start + timedelta(seconds=i * (40.000 / 4)),
                lateral_g=1.1,
                speed_kmh=80.0,
                gps_lat=12.9716,
                gps_lng=77.5946,
                lap_number=3,
            )

        # Lap 3 is in progress because lap 3 is the max lap and ended_at is None.
        # Completed laps are Lap 1 (65.432s) and Lap 2 (48.320s).
        # Best lap should be Lap 2: "0:48.320"
        data = SessionSerializer(self.session).data
        self.assertEqual(data["best_lap"], "0:48.320")
        self.assertEqual(data["laps"], 3)

        # When session ends, Lap 3 is now completed -> best_lap becomes "0:40.000"
        self.session.ended_at = lap3_start + timedelta(seconds=40)
        self.session.save()

        data_ended = SessionSerializer(self.session).data
        self.assertEqual(data_ended["best_lap"], "0:40.000")

    def test_laps_with_fewer_than_five_readings_ignored(self):
        """Laps with fewer than 5 readings are ignored for best_lap."""
        base_time = self.now

        # Lap 1: 4 readings spanning 45.000 seconds (completed because Lap 2 exists)
        for i in range(4):
            Telemetry.objects.create(
                session=self.session,
                recorded_at=base_time + timedelta(seconds=i * 15),
                lateral_g=0.9,
                speed_kmh=60.0,
                gps_lat=12.9716,
                gps_lng=77.5946,
                lap_number=1,
            )

        # Lap 2: 5 readings spanning 55.000 seconds (completed because Lap 3 exists)
        lap2_start = base_time + timedelta(seconds=60)
        for i in range(5):
            Telemetry.objects.create(
                session=self.session,
                recorded_at=lap2_start + timedelta(seconds=i * 13.75),
                lateral_g=1.0,
                speed_kmh=65.0,
                gps_lat=12.9716,
                gps_lng=77.5946,
                lap_number=2,
            )

        # Lap 3: 5 readings (in-progress)
        lap3_start = base_time + timedelta(seconds=130)
        for i in range(5):
            Telemetry.objects.create(
                session=self.session,
                recorded_at=lap3_start + timedelta(seconds=i * 10),
                lateral_g=1.0,
                speed_kmh=65.0,
                gps_lat=12.9716,
                gps_lng=77.5946,
                lap_number=3,
            )

        # Lap 1 has only 4 readings (< 5) -> ignored despite being shorter (45s).
        # Lap 2 has 5 readings (55s) -> selected.
        data = SessionSerializer(self.session).data
        self.assertEqual(data["best_lap"], "0:55.000")
