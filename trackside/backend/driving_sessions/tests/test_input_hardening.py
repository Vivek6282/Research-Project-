"""
Trackside — Input hardening for sessions, notes and biometric readings.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from driving_sessions.models import Session, SessionNote
from tracks.models import Track, Zone

User = get_user_model()


class InputBase(APITestCase):
    """A coach, a driver, two tracks with one corner each, and a running session on the first track."""

    def setUp(self):
        """Create the people, tracks and session."""
        make = lambda e, r: User.objects.create_user(email=e, name=e, password="Passw0rd!12345", role=r)
        self.coach, self.driver = make("in_coach@t.local", "coach"), make("in_driver@t.local", "driver")
        self.track, self.other_track = Track.objects.create(name="Input Track"), Track.objects.create(name="Other Track")
        self.zone = Zone.objects.create(track=self.track, label="T1", threshold_g=1.2)
        self.other_zone = Zone.objects.create(track=self.other_track, label="T9", threshold_g=1.2)
        self.session = Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now())

    def new_session(self, user, **fields):
        """POST a new session as this user."""
        self.client.force_authenticate(user)
        body = {"driver": str(self.driver.id), "track": str(self.track.id), "started_at": timezone.now().isoformat()}
        body.update(fields)
        return self.client.post("/api/sessions/", body, format="json")


class TestSessionInput(InputBase):
    """Who a session can belong to, and what a driver can set."""

    def test_coach_cannot_create_a_session_for_a_coach_or_admin(self):
        """The driver must be an active driver account."""
        self.assertEqual(self.new_session(self.coach, driver=str(self.coach.id)).status_code, 400)
        self.assertEqual(self.new_session(self.coach).status_code, 201)

    def test_driver_cannot_mark_their_own_goal_as_passed(self):
        """goal_passed sent by a driver is ignored (stored as not yet judged)."""
        response = self.new_session(self.driver, goal_text="Zero red at T1", goal_passed=True)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Session.objects.get(pk=response.json()["id"]).goal_passed)

    def test_goal_text_has_a_maximum_length(self):
        """500 characters fit; 501 are refused."""
        self.assertEqual(self.new_session(self.coach, goal_text="g" * 500).status_code, 201)
        self.assertEqual(self.new_session(self.coach, goal_text="g" * 501).status_code, 400)


class TestNoteInput(InputBase):
    """Coach notes: length and which corner they may point at."""

    def post_note(self, **fields):
        """POST a note to the session as the coach."""
        self.client.force_authenticate(self.coach)
        return self.client.post(f"/api/sessions/{self.session.id}/notes/", fields, format="json")

    def test_note_length_is_limited_and_blank_is_refused(self):
        """2000 characters fit; 2001 and an empty note are refused."""
        self.assertEqual(self.post_note(note_text="n" * 2000).status_code, 201)
        self.assertEqual(self.post_note(note_text="n" * 2001).status_code, 400)
        self.assertEqual(self.post_note(note_text="").status_code, 400)

    def test_note_cannot_point_at_a_corner_of_another_track(self):
        """400 and nothing stored for another track's corner; the session's own corner works."""
        self.assertEqual(self.post_note(note_text="Brake later", zone=str(self.other_zone.id)).status_code, 400)
        self.assertEqual(SessionNote.objects.count(), 0)
        self.assertEqual(self.post_note(note_text="Brake later", zone=str(self.zone.id)).status_code, 201)


class TestBiometricInput(InputBase):
    """Biometric readings must be physically possible and not from the future."""

    def post_reading(self, **changes):
        """POST one reading to the session as the driver."""
        self.client.force_authenticate(self.driver)
        body = {"recorded_at": timezone.now().isoformat(), "heart_rate": 90, "spo2": 98, "breathing_rate": 15}
        body.update(changes)
        return self.client.post(f"/api/sessions/{self.session.id}/biometrics/", body, format="json")

    def test_impossible_values_are_refused(self):
        """Heart rate 5 or 999, SpO2 120, breathing 0, a time an hour ahead: all 400."""
        bad = [{"heart_rate": 5}, {"heart_rate": 999}, {"spo2": 120}, {"breathing_rate": 0},
               {"recorded_at": (timezone.now() + timedelta(hours=1)).isoformat()}]
        for change in bad:
            self.assertEqual(self.post_reading(**change).status_code, 400, change)

    def test_a_normal_reading_is_stored(self):
        """A believable reading still gets through."""
        self.assertEqual(self.post_reading().status_code, 201)
