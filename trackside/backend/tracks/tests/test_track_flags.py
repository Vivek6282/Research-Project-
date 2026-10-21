"""
Trackside — Tests for the Track flags added for custom maps (C1).

Covers: default values, the Demo Circuit data migration, seed_demo marking the
Demo Circuit as built-in, and the new read-only fields in the API.
"""

import importlib
import io

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from tracks.models import Track

User = get_user_model()

migration = importlib.import_module("tracks.migrations.0005_mark_demo_circuit_builtin")


class TestTrackFlags(APITestCase):
    """Tests for is_builtin, is_archived and source."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        self.admin = User.objects.create_user(
            email="flags_admin@trackside.local", name="Flags Admin",
            password="AdminPassword123!", role="admin",
        )

    def test_new_track_defaults_to_manual_unlocked_and_active(self):
        """A track made by hand is not built-in, not archived, source manual."""
        track = Track.objects.create(name="Plain Track")
        self.assertFalse(track.is_builtin)
        self.assertFalse(track.is_archived)
        self.assertEqual(track.source, Track.Source.MANUAL)

    def test_data_migration_marks_only_demo_circuit(self):
        """The data migration locks 'Demo Circuit' and leaves other tracks alone."""
        demo = Track.objects.create(name="Demo Circuit")
        other = Track.objects.create(name="Other Track")
        migration.mark_demo_circuit_builtin(apps, None)
        demo.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(demo.is_builtin)
        self.assertEqual(demo.source, Track.Source.BUILTIN)
        self.assertFalse(other.is_builtin)

    def test_data_migration_reverse_unlocks_demo_circuit(self):
        """Reversing the data migration clears the built-in flag."""
        demo = Track.objects.create(name="Demo Circuit", is_builtin=True, source="builtin")
        migration.unmark_demo_circuit_builtin(apps, None)
        demo.refresh_from_db()
        self.assertFalse(demo.is_builtin)

    def test_seed_demo_creates_demo_circuit_as_builtin(self):
        """On a fresh database seed_demo creates the Demo Circuit already locked."""
        User.objects.create_user(
            email="flags_driver@trackside.local", name="Flags Driver",
            password="DriverPassword123!", role="driver",
        )
        call_command(
            "seed_demo", driver_email="flags_driver@trackside.local",
            stdout=io.StringIO(), stderr=io.StringIO(),
        )
        demo = Track.objects.get(name="Demo Circuit")
        self.assertTrue(demo.is_builtin)
        self.assertEqual(demo.source, Track.Source.BUILTIN)

    def test_api_shows_flags_and_ignores_writes_to_them(self):
        """The flags are in the track API and cannot be set through POST."""
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/tracks/",
            {"name": "Sneaky", "is_builtin": True, "is_archived": True, "source": "vbo"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_builtin"])
        self.assertFalse(response.data["is_archived"])
        self.assertEqual(response.data["source"], "manual")
