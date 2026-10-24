"""
Trackside — Phase 2.1: phone readings, real-time sessions and the phone calibration endpoint.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from driving_sessions.models import Session, Telemetry
from driving_sessions.phone_placement import Placer, placement_profile
from tracks.models import Track
from tracks.tests.track_factory import make_imported_track
from tracks.track_profile import build_track_profile

User = get_user_model()


class PhoneBase(APITestCase):
    """A coach, a consenting driver, a driver without consent, a four-corner GPS map and a real-time session."""

    def setUp(self):
        """Create the people, the map and the session."""
        cache.clear()
        make = lambda e, r: User.objects.create_user(email=e, name=e, password="Passw0rd!12345", role=r)
        self.coach, self.driver, self.other = make("ph_coach@t.local", "coach"), make("ph_drv@t.local", "driver"), make("ph_oth@t.local", "driver")
        User.objects.filter(pk=self.driver.pk).update(consent_recorded_at=timezone.now())
        self.driver.refresh_from_db()
        self.track = make_imported_track(self.coach)
        self.profile = build_track_profile(self.track)
        # Started an hour ago, so readings up to an hour after the start are not "from the future"
        self.session = Session.objects.create(driver=self.driver, track=self.track,
                                              started_at=timezone.now() - timedelta(hours=1),
                                              data_source=Session.DataSource.REAL_TIME)

    def reading(self, index, seconds, **changes):
        """A phone reading at outline point `index`, `seconds` after the start, with a wrong zone and lap on purpose."""
        lat, lng = self.profile["gps"][index % len(self.profile["gps"])]
        body = {"recorded_at": (self.session.started_at + timedelta(seconds=seconds)).isoformat(),
                "lateral_g": 0.6, "speed_kmh": 45.0, "gps_lat": lat, "gps_lng": lng, "lap_number": 99,
                "sequence": int(seconds * 10), "gps_accuracy_m": 4.0}
        body.update(changes)
        return body

    def post(self, user, body, session=None):
        """POST readings as this user."""
        self.client.force_authenticate(user)
        return self.client.post(f"/api/sessions/{(session or self.session).id}/telemetry/", body, format="json")


class TestPlacement(PhoneBase):
    """Corner and lap come from the GPS position, never from the phone."""

    def test_server_sets_corner_and_lap_and_ignores_the_phones_values(self):
        """A reading in the middle of corner 1 is stored in corner 1, lap 1, although the phone said lap 99."""
        corner = self.profile["corners"][0]
        middle = (corner["start_index"] + corner["end_index"]) // 2
        response = self.post(self.driver, [self.reading(middle, 1)])
        self.assertEqual(response.status_code, 201, response.content)
        stored = Telemetry.objects.get()
        self.assertEqual((str(stored.zone_id), stored.lap_number), (corner["zone_id"], 1))
        self.assertIsNotNone(stored.received_at)
        self.assertEqual((stored.sequence, stored.gps_accuracy_m), (10, 4.0))

    def test_crossing_the_start_finish_line_starts_the_next_lap(self):
        """Driving the whole outline twice: readings after the line are lap 2, also across two uploads."""
        count = len(self.profile["gps"])
        first_lap = [self.reading(i, i * 0.2) for i in range(0, count, 10)]
        self.assertEqual(self.post(self.driver, first_lap[:60]).status_code, 201)
        self.assertEqual(self.post(self.driver, first_lap[60:]).status_code, 201)
        second = [self.reading(i, 1000 + i * 0.2) for i in range(0, count // 2, 10)]
        self.assertEqual(self.post(self.driver, second).status_code, 201)
        laps = list(Telemetry.objects.order_by("recorded_at").values_list("lap_number", flat=True))
        self.assertEqual(set(laps[:len(first_lap)]), {1})
        self.assertEqual(set(laps[len(first_lap):]), {2})

    def test_far_from_the_track_has_no_corner(self):
        """A position 500 m away (pit car park) is a straight."""
        lat, lng = self.profile["gps"][0]
        self.assertEqual(self.post(self.driver, [self.reading(0, 1, gps_lat=lat + 0.0045, gps_lng=lng)]).status_code, 201)
        self.assertIsNone(Telemetry.objects.get().zone_id)

    def test_placer_follows_the_nearby_point_first(self):
        """Unit check: the placer finds the exact outline point for each GPS point."""
        placer = Placer(placement_profile(self.track))
        for index in (0, 50, 120):
            lat, lng = self.profile["gps"][index]
            placer.place(lat, lng)
            self.assertEqual(placer.last_index, index)


class TestWhoMaySend(PhoneBase):
    """Consent, real-time sessions, ownership and required GPS."""

    def test_simulator_session_refuses_phone_readings(self):
        """409, nothing stored."""
        Session.objects.filter(pk=self.session.pk).update(data_source=Session.DataSource.SIMULATOR)
        self.assertEqual(self.post(self.driver, [self.reading(0, 1)]).status_code, 409)
        self.assertEqual(Telemetry.objects.count(), 0)

    def test_driver_without_consent_is_refused(self):
        """403 on their own real-time session."""
        own = Session.objects.create(driver=self.other, track=self.track, started_at=timezone.now(),
                                     data_source=Session.DataSource.REAL_TIME)
        self.assertEqual(self.post(self.other, [self.reading(0, 1)], session=own).status_code, 403)

    def test_another_drivers_session_is_refused(self):
        """403, as for every session-scoped route."""
        self.assertEqual(self.post(self.other, [self.reading(0, 1)]).status_code, 403)

    def test_phone_readings_need_gps_and_valid_accuracy(self):
        """No GPS: 400. Accuracy 5000 m: 400."""
        self.assertEqual(self.post(self.driver, [self.reading(0, 1, gps_lat=None, gps_lng=None)]).status_code, 400)
        self.assertEqual(self.post(self.driver, [self.reading(0, 1, gps_accuracy_m=5000)]).status_code, 400)

    def test_coach_posting_keeps_the_old_behaviour(self):
        """A coach (simulator, laptop link) still sends its own corner and lap on any session."""
        Session.objects.filter(pk=self.session.pk).update(data_source=Session.DataSource.SIMULATOR)
        self.assertEqual(self.post(self.coach, [self.reading(0, 1)]).status_code, 201)
        self.assertEqual(Telemetry.objects.get().lap_number, 99)


class TestRealTimeSessions(PhoneBase):
    """Only staff set a session to real time, and only on a GPS map."""

    def create(self, user, track, source):
        """POST a session for the driver."""
        self.client.force_authenticate(user)
        return self.client.post("/api/sessions/", {"driver": str(self.driver.id), "track": str(track.id),
                                                   "started_at": timezone.now().isoformat(), "data_source": source}, format="json")

    def test_coach_starts_a_real_time_session_on_a_gps_map(self):
        """201 with data_source real_time."""
        response = self.create(self.coach, self.track, "real_time")
        self.assertEqual((response.status_code, response.json()["data_source"]), (201, "real_time"))

    def test_the_schematic_demo_circuit_cannot_be_real_time(self):
        """The built-in map has no GPS outline: 400 on data_source."""
        demo = Track.objects.create(name="Demo Circuit", is_builtin=True, source="builtin")
        response = self.create(self.coach, demo, "real_time")
        self.assertEqual(response.status_code, 400)
        self.assertIn("data_source", response.json())

    def test_a_driver_cannot_make_their_own_session_real_time(self):
        """The driver's own session is always simulator."""
        response = self.create(self.driver, self.track, "real_time")
        self.assertEqual((response.status_code, response.json()["data_source"]), (201, "simulator"))


class TestPhoneCalibration(PhoneBase):
    """The phone stores its mounting and warnings; only the session's own driver can."""

    def url(self):
        """The calibration endpoint of the session."""
        return f"/api/sessions/{self.session.id}/phone-calibration/"

    def put(self, user, body):
        """PUT as this user."""
        self.client.force_authenticate(user)
        return self.client.put(self.url(), body, format="json")

    def test_driver_saves_calibration_and_flags_and_coach_reads_them(self):
        """Directions are scaled to length 1; flags are added once; the coach sees them."""
        body = {"gravity": [0, 0, -9.81], "forward": [0, 2, 0], "flags": ["mount_moved", "mount_moved"]}
        response = self.put(self.driver, body)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["phone_calibration"], {"gravity": [0.0, 0.0, -1.0], "forward": [0.0, 1.0, 0.0]})
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.get(self.url()).json()["sensor_flags"], ["mount_moved"])

    def test_bad_calibration_is_refused(self):
        """Forward along gravity, not three numbers, an unknown flag: all 400."""
        for body in ({"gravity": [0, 0, -9.8], "forward": [0, 0, 1]}, {"gravity": [1, 2]}, {"flags": ["phone_on_fire"]}):
            self.assertEqual(self.put(self.driver, body).status_code, 400, body)

    def test_coach_and_other_driver_cannot_save(self):
        """Coach: 403. Another driver: 404 (the session is hidden from them)."""
        self.assertEqual(self.put(self.coach, {"flags": ["mount_moved"]}).status_code, 403)
        self.assertEqual(self.put(self.other, {"flags": ["mount_moved"]}).status_code, 404)
