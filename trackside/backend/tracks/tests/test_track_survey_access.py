"""
Trackside — Tests for who may use the track survey endpoint (C8).

The survey endpoint overwrites a track's outline and survey time, so drivers
and anonymous callers must be refused, and the built-in track stays locked.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from tracks.models import Track

User = get_user_model()
POINTS = [
    {"lat": 11.016800, "lng": 76.955800},
    {"lat": 11.017200, "lng": 76.955800},
    {"lat": 11.017400, "lng": 76.956000},
    {"lat": 11.017400, "lng": 76.956400},
]


class TestTrackSurveyAccess(APITestCase):
    """Role checks for POST /api/tracks/<id>/survey/."""

    def setUp(self):
        """Create the users and data this test class needs."""
        super().setUp()
        make = User.objects.create_user
        self.admin = make(email="sv_admin@trackside.local", name="A", password="AdminPassword123!", role="admin")
        self.coach = make(email="sv_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="sv_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.track = Track.objects.create(name="Survey Access Track", reference_line=[{"lat": 1, "lng": 1}])
        self.url = f"/api/tracks/{self.track.id}/survey/"

    def test_driver_is_refused_and_track_is_unchanged(self):
        """A driver gets 403 and the outline and survey time are untouched."""
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.post(self.url, POINTS, format="json").status_code, 403)
        self.track.refresh_from_db()
        self.assertEqual(self.track.reference_line, [{"lat": 1, "lng": 1}])
        self.assertIsNone(self.track.surveyed_at)

    def test_anonymous_is_refused(self):
        """Logged-out callers cannot survey."""
        self.assertIn(self.client.post(self.url, POINTS, format="json").status_code, (401, 403))

    def test_admin_and_coach_can_survey(self):
        """Both allowed roles get 200 and the outline is replaced."""
        for user in (self.admin, self.coach):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.post(self.url, POINTS, format="json").status_code, 200)
        self.track.refresh_from_db()
        self.assertEqual(len(self.track.reference_line), 4)
        self.assertIsNotNone(self.track.surveyed_at)

    def test_builtin_track_cannot_be_surveyed(self):
        """The built-in track answers 409 and keeps its outline."""
        builtin = Track.objects.create(name="Demo Circuit", is_builtin=True, reference_line=[{"lat": 2, "lng": 2}])
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/tracks/{builtin.id}/survey/", POINTS, format="json")
        self.assertEqual(response.status_code, 409)
        builtin.refresh_from_db()
        self.assertEqual(builtin.reference_line, [{"lat": 2, "lng": 2}])
