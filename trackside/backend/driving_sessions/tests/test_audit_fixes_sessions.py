"""
Trackside — Audit fixes F5 (bad driver id) and F6 (a retried upload does not store readings twice).
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from driving_sessions.models import Alert, Session, Telemetry
from tracks.models import Track, Zone

User = get_user_model()


class TestSummaryDriverParameter(APITestCase):

    def setUp(self):
        self.coach = User.objects.create_user(email="f5coach@t.test", name="Coach", role="coach", password="CoachPass123!")
        self.driver = User.objects.create_user(email="f5drv@t.test", name="Driver", role="driver", password="DriverPass123!")
        self.client.force_authenticate(self.coach)

    def test_a_malformed_driver_id_is_a_400_not_a_crash(self):
        """Text that is not an id is answered 400 with a message."""
        for bad in ("not-a-uuid", "%00", "1" * 80):
            res = self.client.get(f"/api/sessions/alerts/summary/?driver={bad}")
            self.assertEqual(res.status_code, 400, bad)
            self.assertIn("valid driver id", res.json()["detail"])

    def test_an_unknown_driver_is_still_a_404_and_a_real_one_a_200(self):
        """A well-formed id of nobody is 404; a real driver (even with no sessions) is 200."""
        self.assertEqual(self.client.get("/api/sessions/alerts/summary/?driver=00000000-0000-0000-0000-000000000000").status_code, 404)
        self.assertEqual(self.client.get(f"/api/sessions/alerts/summary/?driver={self.driver.id}").status_code, 200)


class TestRetriedUploadsAreNotStoredTwice(APITestCase):

    def setUp(self):
        self.coach = User.objects.create_user(email="f6coach@t.test", name="Coach", role="coach", password="CoachPass123!")
        self.driver = User.objects.create_user(email="f6drv@t.test", name="Driver", role="driver", password="DriverPass123!")
        self.track = Track.objects.create(name="F6 Track", created_by=self.coach)
        self.zone = Zone.objects.create(track=self.track, label="T1", threshold_g=1.0)
        self.session = Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now())
        self.client.force_authenticate(self.coach)
        self.url = f"/api/sessions/{self.session.id}/telemetry/"
        self.base = timezone.now() - timedelta(seconds=30)

    def reading(self, n, g=0.5, lap=1):
        """One reading n tenths of a second after the base time."""
        return {"recorded_at": (self.base + timedelta(seconds=n / 10)).isoformat(), "lateral_g": g, "speed_kmh": 40,
                "gps_lat": 0, "gps_lng": 0, "lap_number": lap, "zone": str(self.zone.id)}

    def stored(self):
        return Telemetry.objects.filter(session=self.session).count()

    def test_a_retried_single_reading_is_stored_once(self):
        """The same reading posted twice leaves one row; the retry is answered 200 'Already stored'."""
        body = self.reading(1)
        self.assertEqual(self.client.post(self.url, body, format="json").status_code, 201)
        retry = self.client.post(self.url, body, format="json")
        self.assertEqual((retry.status_code, retry.json()["duplicates_skipped"]), (200, 1))
        self.assertEqual(self.stored(), 1)

    def test_a_retried_batch_is_stored_once_and_makes_no_extra_alerts(self):
        """A whole batch sent again changes nothing, including the alerts."""
        batch = [self.reading(n, g=1.4) for n in range(5)]            # above the 1.0 limit: alerts
        self.assertEqual(self.client.post(self.url, batch, format="json").status_code, 201)
        alerts_before = Alert.objects.filter(session=self.session).count()
        self.assertEqual(self.client.post(self.url, batch, format="json").status_code, 200)
        self.assertEqual(self.stored(), 5)
        self.assertEqual(Alert.objects.filter(session=self.session).count(), alerts_before)

    def test_a_partly_repeated_batch_stores_only_the_new_readings(self):
        """Two repeated readings and three new ones: three rows are added."""
        self.client.post(self.url, [self.reading(0), self.reading(1)], format="json")
        res = self.client.post(self.url, [self.reading(0), self.reading(1), self.reading(2), self.reading(3), self.reading(4)], format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.stored(), 5)

    def test_repeats_inside_one_batch_are_stored_once(self):
        """The same reading twice in a single batch gives one row."""
        self.client.post(self.url, [self.reading(7), self.reading(7)], format="json")
        self.assertEqual(self.stored(), 1)

    def test_different_readings_at_the_same_time_are_kept(self):
        """Same moment but a different g is a different reading, so both are stored."""
        self.client.post(self.url, [self.reading(9, g=0.4), self.reading(9, g=0.6)], format="json")
        self.assertEqual(self.stored(), 2)

    def test_the_same_values_in_another_lap_are_kept(self):
        """The lap number is part of the identity."""
        self.client.post(self.url, [self.reading(11, lap=1), self.reading(11, lap=2)], format="json")
        self.assertEqual(self.stored(), 2)
