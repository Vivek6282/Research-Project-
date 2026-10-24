"""
Trackside — Tests for POST /api/devices/events/ (Phase 2.0, task 2).
"""

import uuid

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from devices.event_models import DeviceEvent
from devices.models import Device
from driving_sessions.models import Session
from tracks.models import Track

User = get_user_model()
URL = "/api/devices/events/"


class DeviceEventsBase(APITestCase):
    """Two drivers (A has consent), a coach, A's running session, and a kart unit assigned to A."""

    def setUp(self):
        """Create the people, the session and a kart unit with a known token."""
        make = lambda e, r: User.objects.create_user(email=e, name=e, password="Passw0rd!12345", role=r)
        self.driver_a, self.driver_b = make("ev_a@t.local", "driver"), make("ev_b@t.local", "driver")
        self.coach = make("ev_coach@t.local", "coach")
        User.objects.filter(pk=self.driver_a.pk).update(consent_recorded_at=timezone.now())
        self.driver_a.refresh_from_db()
        self.track = Track.objects.create(name="Event Track")
        self.session = Session.objects.create(driver=self.driver_a, track=self.track, started_at=timezone.now())
        self.device = Device(name="Kart A", device_type=Device.DeviceType.KART_UNIT, assigned_to=self.driver_a)
        self.token = self.device.set_api_key()
        self.device.save()

    def event(self, event_type="crash_suspected", **changes):
        """A valid event body; keyword arguments replace or add fields."""
        body = {"event_id": str(uuid.uuid4()), "event_type": event_type, "session": str(self.session.id),
                "occurred_at": timezone.now().isoformat(), "sequence": 7,
                "payload": {"peak_g": 9.5, "speed_before_kmh": 48.0, "saturated": False,
                            "raw_window": [[0, 1.0, 0.2, 9.8], [10, 6.0, 3.1, 9.8]]}}
        body.update(changes)
        return body

    def as_device(self, body, token=None):
        """POST as the kart unit."""
        self.client.force_authenticate(user=None)
        return self.client.post(URL, body, format="json", HTTP_X_DEVICE_TOKEN=token or self.token)

    def as_user(self, user, body):
        """POST signed in as a person."""
        self.client.force_authenticate(user=user)
        return self.client.post(URL, body, format="json")


class TestStoringEvents(DeviceEventsBase):
    """What is stored and how retries behave."""

    def test_device_crash_event_is_stored_with_both_times_and_the_counter(self):
        """201; device time and sequence kept, server time added, sender recorded."""
        response = self.as_device(self.event())
        self.assertEqual(response.status_code, 201, response.content)
        stored = DeviceEvent.objects.get()
        self.assertEqual((stored.device_id, stored.sent_by_id, stored.sequence), (self.device.id, None, 7))
        self.assertIsNotNone(stored.received_at)
        self.assertEqual(stored.session_id, self.session.id)

    def test_a_retry_returns_the_stored_event_and_never_duplicates(self):
        """Same event_id twice from the same device: 201 then 200 with the same id, one row."""
        body = self.event()
        first, second = self.as_device(body), self.as_device(body)
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(DeviceEvent.objects.count(), 1)

    def test_someone_elses_event_id_is_refused(self):
        """The device's event_id reused by driver A's phone: 409, nothing new stored."""
        body = self.event()
        self.as_device(body)
        self.assertEqual(self.as_user(self.driver_a, body).status_code, 409)
        self.assertEqual(DeviceEvent.objects.count(), 1)

    def test_consenting_driver_phone_can_send_a_crash_and_driver_ok(self):
        """Driver A's phone: crash 201, then "I'm OK" pointing at it 201."""
        crash = self.event()
        self.assertEqual(self.as_user(self.driver_a, crash).status_code, 201)
        ok = self.event("driver_ok", payload={"crash_event_id": crash["event_id"]})
        self.assertEqual(self.as_user(self.driver_a, ok).status_code, 201)
        self.assertEqual(DeviceEvent.objects.get(event_type="driver_ok").sent_by_id, self.driver_a.id)

    def test_heartbeat_needs_no_session(self):
        """A device heartbeat without a session is stored."""
        body = self.event("heartbeat", session=None, payload={"firmware_version": "2.0.1", "battery_mv": 3900})
        self.assertEqual(self.as_device(body).status_code, 201)


class TestRefusedEvents(DeviceEventsBase):
    """Who cannot send, and which bodies are refused."""

    def test_driver_without_consent_is_refused_before_the_body_is_read(self):
        """Driver B has no consent recorded: 403 even for an empty body."""
        self.assertEqual(self.as_user(self.driver_b, {}).status_code, 403)

    def test_coach_and_anonymous_cannot_send(self):
        """Coaches are refused (403); nobody signed in is refused (401/403)."""
        self.assertEqual(self.as_user(self.coach, self.event()).status_code, 403)
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.post(URL, self.event(), format="json").status_code, (401, 403))

    def test_wrong_device_token_is_refused(self):
        """A made-up token gets 401/403."""
        self.assertIn(self.as_device(self.event(), token="dt_not-a-real-token").status_code, (401, 403))

    def test_someone_elses_session_looks_missing(self):
        """Driver B's session and a made-up session id give the same 404 to driver A."""
        other = Session.objects.create(driver=self.driver_b, track=self.track, started_at=timezone.now())
        hidden = self.as_user(self.driver_a, self.event(session=str(other.id)))
        missing = self.as_user(self.driver_a, self.event(session=str(uuid.uuid4())))
        self.assertEqual((hidden.status_code, hidden.json()), (missing.status_code, missing.json()))
        self.assertEqual(hidden.status_code, 404)

    def test_ended_session_takes_no_new_events(self):
        """409 once the session has ended."""
        Session.objects.filter(pk=self.session.pk).update(ended_at=timezone.now())
        self.assertEqual(self.as_device(self.event()).status_code, 409)

    def test_phone_cannot_send_a_self_test_result(self):
        """Self-test results come from devices only."""
        body = self.event("self_test_result", payload={"passed": True})
        self.assertEqual(self.as_user(self.driver_a, body).status_code, 403)

    def test_bad_payloads_are_refused(self):
        """Missing peak_g, unknown field, out-of-range speed, bad sample rows, oversize payload: all 400."""
        bad_payloads = [{"speed_before_kmh": 40}, {"peak_g": 5, "colour": "red"}, {"peak_g": 5, "speed_before_kmh": 900},
                        {"peak_g": 5, "raw_window": [["a"]]}, {"peak_g": 5, "raw_window": [[1.0] * 8] * 400}]
        for payload in bad_payloads:
            self.assertEqual(self.as_device(self.event(payload=payload)).status_code, 400, payload)
        self.assertEqual(DeviceEvent.objects.count(), 0)

    def test_crash_needs_a_session_and_driver_ok_needs_a_real_crash(self):
        """Crash without session: 400. "Driver OK" for an unknown crash id: 400."""
        self.assertEqual(self.as_device(self.event(session=None)).status_code, 400)
        ok = self.event("driver_ok", payload={"crash_event_id": str(uuid.uuid4())})
        self.assertEqual(self.as_user(self.driver_a, ok).status_code, 400)

    def test_negative_sequence_and_unknown_type_are_refused(self):
        """The envelope is checked too."""
        self.assertEqual(self.as_device(self.event(sequence=-1)).status_code, 400)
        self.assertEqual(self.as_device(self.event("explosion")).status_code, 400)
