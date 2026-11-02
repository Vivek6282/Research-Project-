"""
Trackside — Tests for the Track flags added for custom maps (C1).

Covers: default values and the read-only fields in the API.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tracks.models import Track

User = get_user_model()


class TestTrackFlags(APITestCase):
    """Tests for is_archived and source."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        self.admin = User.objects.create_user(
            email="flags_admin@trackside.local", name="Flags Admin",
            password="AdminPassword123!", role="admin",
        )

    def test_new_track_defaults_to_manual_and_active(self):
        """A track made by hand is not archived, source manual."""
        track = Track.objects.create(name="Plain Track")
        self.assertFalse(track.is_archived)
        self.assertEqual(track.source, Track.Source.MANUAL)

    def test_api_shows_flags_and_ignores_writes_to_them(self):
        """The flags are in the track API and cannot be set through POST."""
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/tracks/",
            {"name": "Sneaky", "is_archived": True, "source": "vbo"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_archived"])
        self.assertEqual(response.data["source"], "manual")
