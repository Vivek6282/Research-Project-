"""
Trackside — Tests for Session.is_demo (H5).

Demo runs are marked so they are never mistaken for real driving.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from driving_sessions.models import Session
from tracks.models import Track

User = get_user_model()


class TestSessionIsDemo(APITestCase):
    """The flag defaults to False, shows in the API, and cannot be set by API clients."""

    def setUp(self):
        """Create a coach, a driver, a track and one session."""
        super().setUp()
        make = User.objects.create_user
        self.coach = make(email="demo_flag_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        self.driver = make(email="demo_flag_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        self.track = Track.objects.create(name="Flag Track")
        self.session = Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now())

    def test_default_is_false(self):
        """A normal session is not a demo."""
        self.assertFalse(self.session.is_demo)

    def test_api_shows_the_flag_to_coach_and_driver(self):
        """Both lists include is_demo so the UI can label demo runs."""
        Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now(), is_demo=True)
        for user in (self.coach, self.driver):
            self.client.force_authenticate(user)
            rows = self.client.get("/api/sessions/").data["results"]
            self.assertEqual(sorted(r["is_demo"] for r in rows), [False, True])

    def test_clients_cannot_set_the_flag(self):
        """POST and PATCH ignore is_demo, so a normal user cannot disguise a session."""
        self.client.force_authenticate(self.coach)
        body = {"driver": str(self.driver.id), "track": str(self.track.id), "mode": "safety",
                "started_at": timezone.now().isoformat(), "is_demo": True}
        response = self.client.post("/api/sessions/", body, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(Session.objects.get(pk=response.data["id"]).is_demo)
        self.client.patch(f"/api/sessions/{self.session.id}/", {"is_demo": True}, format="json")
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_demo)


class TestRosterShowsActiveFlag(APITestCase):
    """The roster says which drivers are active, so the Play demo dialog can list only those."""

    def test_roster_entries_have_is_active(self):
        """A deactivated driver is in the roster with is_active False."""
        coach = User.objects.create_user(email="ra_coach@trackside.local", name="C", password="CoachPassword123!", role="coach")
        User.objects.create_user(email="ra_on@trackside.local", name="On Driver", password="DriverPassword123!", role="driver")
        User.objects.create_user(email="ra_off@trackside.local", name="Off Driver", password="DriverPassword123!", role="driver", is_active=False)
        self.client.force_authenticate(coach)
        roster = {r["driver_name"]: r["is_active"] for r in self.client.get("/api/sessions/roster-status/").data["roster"]}
        self.assertEqual(roster, {"On Driver": True, "Off Driver": False})


class TestDriverSummaryShowsDemoFlag(APITestCase):
    """The driver dashboard's latest session says whether it was a demo run."""

    def test_latest_session_carries_is_demo(self):
        """A demo run shows is_demo True; a later real session shows False."""
        driver = User.objects.create_user(email="ds_driver@trackside.local", name="D", password="DriverPassword123!", role="driver")
        track = Track.objects.create(name="Summary Track")
        Session.objects.create(driver=driver, track=track, started_at=timezone.now(), is_demo=True)
        self.client.force_authenticate(driver)
        self.assertTrue(self.client.get("/api/sessions/alerts/summary/").data["latest_session"]["is_demo"])
        Session.objects.create(driver=driver, track=track, started_at=timezone.now() + timezone.timedelta(minutes=5))
        self.assertFalse(self.client.get("/api/sessions/alerts/summary/").data["latest_session"]["is_demo"])
