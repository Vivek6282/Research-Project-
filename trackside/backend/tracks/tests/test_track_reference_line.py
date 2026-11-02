"""
Trackside — Unit tests for Track Reference Line endpoint.

Tests that the GET /api/tracks/<uuid>/reference-line/ endpoint correctly
returns the track's surveyed GPS polyline scoped to authenticated users,
and returns null when no survey has been done.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from tracks.models import Track

User = get_user_model()


class TestTrackReferenceLineEndpoint(APITestCase):
    """Tests for GET /api/tracks/<uuid>/reference-line/"""

    def setUp(self):
        super().setUp()
        # Create a coach user
        self.coach = User.objects.create_user(
            email="coach_refline@trackside.local",
            name="Coach RefLine",
            password="CoachPassword123!",
            role="coach",
        )

        # Create a surveyed track with reference_line data
        self.surveyed_track = Track.objects.create(
            name="Surveyed Test Track",
            reference_line=[
                {"lat": 11.016842, "lng": 76.955831},
                {"lat": 11.017120, "lng": 76.956110},
                {"lat": 11.017400, "lng": 76.956400},
                {"lat": 11.017200, "lng": 76.956600},
                {"lat": 11.016842, "lng": 76.955831},
            ],
        )

        # Create an unsurveyed track without reference_line
        self.unsurveyed_track = Track.objects.create(
            name="Unsurveyed Test Track",
            reference_line=None,
        )

    def test_coach_gets_reference_line_for_surveyed_track(self):
        """Coach can retrieve the reference_line GPS polyline for a surveyed track."""
        self.client.force_authenticate(user=self.coach)
        url = f"/api/tracks/{self.surveyed_track.id}/reference-line/"
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["track_id"] == str(self.surveyed_track.id)
        assert data["track_name"] == "Surveyed Test Track"
        assert data["reference_line"] is not None
        assert isinstance(data["reference_line"], list)
        assert len(data["reference_line"]) == 5
        # Verify point structure
        assert data["reference_line"][0]["lat"] == 11.016842
        assert data["reference_line"][0]["lng"] == 76.955831

    def test_returns_null_reference_line_for_unsurveyed_track(self):
        """Endpoint returns reference_line: null when the track hasn't been surveyed."""
        self.client.force_authenticate(user=self.coach)
        url = f"/api/tracks/{self.unsurveyed_track.id}/reference-line/"
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["track_id"] == str(self.unsurveyed_track.id)
        assert data["reference_line"] is None

    def test_unauthenticated_request_is_rejected(self):
        """Unauthenticated requests are rejected with 401 or 403."""
        url = f"/api/tracks/{self.surveyed_track.id}/reference-line/"
        response = self.client.get(url)

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_nonexistent_track_returns_404(self):
        """Requesting reference-line for a non-existent track returns 404."""
        import uuid
        self.client.force_authenticate(user=self.coach)
        fake_id = uuid.uuid4()
        url = f"/api/tracks/{fake_id}/reference-line/"
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStoredReferenceLine(APITestCase):
    """A map answers with its own stored outline and corners."""

    def setUp(self):
        super().setUp()
        self.coach = User.objects.create_user(
            email="coach_stored@trackside.local", name="Coach Stored",
            password="CoachPassword123!", role="coach",
        )
        self.client.force_authenticate(user=self.coach)

    def test_custom_map_is_unchanged(self):
        """Same reference_line as stored, corners from stored gps_range."""
        from tracks.models import Zone
        line = [{"lat": 11.0, "lng": 76.9}, {"lat": 11.001, "lng": 76.901}]
        track = Track.objects.create(name="Mine", reference_line=line)
        Zone.objects.create(track=track, label="T1", threshold_g=1.2, gps_range={
            "start": {"lat": 11.0, "lng": 76.9}, "end": {"lat": 11.001, "lng": 76.901}})
        data = self.client.get(f"/api/tracks/{track.id}/reference-line/").json()
        assert "is_schematic" not in data
        assert data["reference_line"] == line
        assert [c["label"] for c in data["corners"]] == ["T1"]
        assert data["corners"][0]["start"] == {"lat": 11.0, "lng": 76.9}
