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
        self.track = Track.objects.create(name="Seed Map", kart_class=Track.KartClass.SPRINT)
        for label, limit in (("Hairpin", 1.15), ("Sweeper", 1.4), ("Chicane", 1.3)):
            Zone.objects.create(track=self.track, label=label, threshold_g=limit)

    def seed(self, out=None, **extra):
        """Run seed_demo on the test map."""
        return call_command("seed_demo", driver_email=self.driver.email, track_name="Seed Map", stdout=out or io.StringIO(), **extra)

    def test_seed_demo_creates_objects_and_prints_lines(self):
        """seed_demo creates a device and a session on the chosen map and prints ready-to-paste lines."""
        out = io.StringIO()
        self.seed(out)
        output = out.getvalue()

        # Check stdout lines
        self.assertIn("BACKEND_URL=http://localhost:8000", output)
        self.assertIn("SESSION_ID=", output)
        self.assertIn("DEVICE_TOKEN=dt_", output)
        self.assertIn('DEMO_ZONES={"Hairpin":', output)

        # The map's corners are used as they are
        track = self.track
        self.assertEqual({z.label: z.threshold_g for z in track.zones.all()}, {"Hairpin": 1.15, "Sweeper": 1.4, "Chicane": 1.3})
        self.assertEqual(Track.objects.count(), 1)

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
        self.seed(out1)
        tracks_count1 = Track.objects.count()
        zones_count1 = Zone.objects.count()
        devices_count1 = Device.objects.filter(assigned_to=self.driver).count()
        sessions_count1 = Session.objects.filter(driver=self.driver).count()

        out2 = io.StringIO()
        self.seed(out2)
        output2 = out2.getvalue()

        self.assertEqual(Track.objects.count(), tracks_count1)
        self.assertEqual(Zone.objects.count(), zones_count1)
        self.assertEqual(Device.objects.filter(assigned_to=self.driver).count(), devices_count1)
        self.assertEqual(Session.objects.filter(driver=self.driver).count(), sessions_count1 + 1)

        # Token was not regenerated, so DEVICE_TOKEN is not in output2
        self.assertNotIn("DEVICE_TOKEN=", output2)

        # When --new-token is passed, token IS regenerated
        out3 = io.StringIO()
        self.seed(out3, new_token=True)
        self.assertIn("DEVICE_TOKEN=dt_", out3.getvalue())

    def test_seed_demo_refuses_in_production(self):
        """seed_demo refuses to run when DJANGO_ENV is production."""
        with patch.dict(os.environ, {"DJANGO_ENV": "production"}):
            with self.assertRaises(CommandError) as ctx:
                self.seed()
            self.assertIn("cannot be run in production", str(ctx.exception))

    def test_seed_demo_needs_an_existing_map_with_the_three_corners(self):
        """An unknown or archived map, and a map missing a corner, give a clear error and create nothing."""
        with self.assertRaisesRegex(CommandError, "No active map called 'Nope'"):
            call_command("seed_demo", driver_email=self.driver.email, track_name="Nope", stdout=io.StringIO())
        Zone.objects.filter(track=self.track, label="Chicane").delete()
        with self.assertRaisesRegex(CommandError, "no corner called Chicane"):
            self.seed()
        Track.objects.filter(pk=self.track.pk).update(is_archived=True)
        with self.assertRaisesRegex(CommandError, "No active map"):
            self.seed()
        self.assertEqual(Session.objects.count(), 0)
        self.assertEqual(Track.objects.count(), 1)
