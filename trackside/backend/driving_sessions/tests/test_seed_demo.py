"""
Trackside — Tests for seed_demo management command.
"""

import io
import os
import json
from unittest.mock import patch
from django.core.management import call_command, CommandError
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tracks.models import Track, Zone
from devices.models import Device
from driving_sessions.models import Session

User = get_user_model()


class TestSeedDemoCommand(APITestCase):

    def setUp(self):
        super().setUp()
        self.driver = User.objects.create_user(
            email="demo_driver@trackside.local",
            name="Demo Driver",
            role="driver",
            password="DriverPassword123!",
        )

    def test_seed_demo_creates_objects_and_prints_lines(self):
        """seed_demo creates track, zones, device, session and prints ready-to-paste lines."""
        out = io.StringIO()
        call_command("seed_demo", driver_email=self.driver.email, stdout=out)
        output = out.getvalue()

        # Check stdout lines
        self.assertIn("BACKEND_URL=http://localhost:8000", output)
        self.assertIn("SESSION_ID=", output)
        self.assertIn("DEVICE_TOKEN=dt_", output)
        self.assertIn('DEMO_ZONES={"Hairpin":', output)

        # Check track and zones
        track = Track.objects.get(name="Demo Circuit")
        self.assertEqual(track.kart_class, Track.KartClass.SPRINT)

        hairpin = Zone.objects.get(track=track, label="Hairpin")
        self.assertEqual(hairpin.threshold_g, 1.15)
        self.assertEqual(hairpin.corner_type, Zone.CornerType.HAIRPIN)

        sweeper = Zone.objects.get(track=track, label="Sweeper")
        self.assertEqual(sweeper.threshold_g, 1.55)
        self.assertEqual(sweeper.corner_type, Zone.CornerType.SWEEPER)

        chicane = Zone.objects.get(track=track, label="Chicane")
        self.assertEqual(chicane.threshold_g, 1.30)
        self.assertEqual(chicane.corner_type, Zone.CornerType.CHICANE)

        # Check device
        device = Device.objects.get(device_type=Device.DeviceType.KART_UNIT, assigned_to=self.driver)
        self.assertTrue(device.api_key_hash)

        # Check session
        session = Session.objects.filter(driver=self.driver, track=track).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.mode, Session.Mode.SAFETY)
        self.assertEqual(session.kart_number, "demo")

    def test_seed_demo_is_idempotent_and_reuses_objects(self):
        """Running seed_demo twice reuses track, zones and device, while creating a new session."""
        out1 = io.StringIO()
        call_command("seed_demo", driver_email=self.driver.email, stdout=out1)
        tracks_count1 = Track.objects.filter(name="Demo Circuit").count()
        zones_count1 = Zone.objects.filter(track__name="Demo Circuit").count()
        devices_count1 = Device.objects.filter(assigned_to=self.driver).count()
        sessions_count1 = Session.objects.filter(driver=self.driver).count()

        out2 = io.StringIO()
        call_command("seed_demo", driver_email=self.driver.email, stdout=out2)
        output2 = out2.getvalue()

        self.assertEqual(Track.objects.filter(name="Demo Circuit").count(), tracks_count1)
        self.assertEqual(Zone.objects.filter(track__name="Demo Circuit").count(), zones_count1)
        self.assertEqual(Device.objects.filter(assigned_to=self.driver).count(), devices_count1)
        self.assertEqual(Session.objects.filter(driver=self.driver).count(), sessions_count1 + 1)

        # Token was not regenerated, so DEVICE_TOKEN is not in output2
        self.assertNotIn("DEVICE_TOKEN=", output2)

        # When --new-token is passed, token IS regenerated
        out3 = io.StringIO()
        call_command("seed_demo", driver_email=self.driver.email, new_token=True, stdout=out3)
        self.assertIn("DEVICE_TOKEN=dt_", out3.getvalue())

    def test_seed_demo_refuses_in_production(self):
        """seed_demo refuses to run when DJANGO_ENV is production."""
        with patch.dict(os.environ, {"DJANGO_ENV": "production"}):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_demo", driver_email=self.driver.email)
            self.assertIn("cannot be run in production", str(ctx.exception))
