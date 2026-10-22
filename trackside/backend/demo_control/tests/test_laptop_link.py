"""
Trackside — Tests for the laptop link (a laptop's simulator feeds a hosted session).
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from devices.models import Device
from driving_sessions.models import Session, Telemetry

User = get_user_model()
START, STOP, STATUS = "/api/laptop-link/start/", "/api/laptop-link/stop/", "/api/laptop-link/status/"


class LaptopLinkTests(APITestCase):
    """Who can use it, what it creates, and that the token does only what a device token may."""

    def setUp(self):
        """A coach, a driver and a signed-in client."""
        super().setUp()
        make = lambda e, r, n: User.objects.create_user(email=e, name=n, role=r, password="Passw0rd!12345")
        self.coach = make("ll_coach@example.com", "coach", "Coach")
        self.admin = make("ll_admin@example.com", "admin", "Admin")
        self.driver = make("ll_driver@example.com", "driver", "Ana Driver")
        self.client.force_authenticate(self.coach)

    def start(self):
        """Start a link for the driver; returns the response."""
        return self.client.post(START, {"driver_id": str(self.driver.id)}, format="json")

    def device_client(self, token):
        """A client that authenticates like the laptop's simulator."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Device-Token {token}")
        return client

    def reading(self, zone_id, seconds_ago=0):
        """One telemetry reading body."""
        return {"recorded_at": (timezone.now() - timedelta(seconds=seconds_ago)).isoformat(), "lateral_g": 1.0,
                "speed_kmh": 50.0, "gps_lat": 10.0, "gps_lng": 76.0, "lap_number": 1, "zone": zone_id}

    def test_only_coach_and_admin_may_use_it(self):
        """A driver gets 403 and a signed-out caller is refused; an admin may start a link."""
        self.client.force_authenticate(self.driver)
        self.assertEqual(self.client.post(START, {"driver_id": str(self.driver.id)}, format="json").status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(STATUS).status_code, (401, 403))
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.start().status_code, 200)

    def test_start_returns_session_token_zones_and_marks_the_run_as_demo(self):
        """The response has what the laptop needs; the session is open, on the Demo Circuit and marked demo."""
        body = self.start().json()
        self.assertTrue(body["device_token"].startswith("dt_"))
        self.assertEqual(set(body["zones"]), {"Hairpin", "Sweeper", "Chicane"})
        self.assertTrue(body["backend_url"].startswith("http"))
        session = Session.objects.get(pk=body["session_id"])
        self.assertEqual((session.driver_id, session.is_demo, session.ended_at, session.track.name),
                         (self.driver.id, True, None, "Demo Circuit"))
        self.assertEqual(self.client.get(STATUS).json()["state"], "waiting")

    def test_the_token_posts_readings_then_finishing_ends_the_link_and_kills_the_token(self):
        """Readings arrive (status receiving); the simulator's finish call closes the session; the token stops working."""
        body = self.start().json()
        laptop = self.device_client(body["device_token"])
        zone = body["zones"]["Hairpin"]
        self.assertEqual(laptop.post(f"/api/sessions/{body['session_id']}/telemetry/", [self.reading(zone)], format="json").status_code, 201)
        self.assertEqual(self.client.get(STATUS).json()["state"], "receiving")
        self.assertEqual(laptop.post(f"/api/sessions/{body['session_id']}/finish/").status_code, 200)
        self.assertEqual(self.client.get(STATUS).json()["state"], "idle")
        after = laptop.post(f"/api/sessions/{body['session_id']}/telemetry/", [self.reading(zone)], format="json")
        self.assertIn(after.status_code, (401, 403, 409))
        self.assertEqual(Device.objects.get(name="Laptop link unit").assigned_to_id, None)

    def test_stop_closes_the_session_drops_the_token_and_can_be_pressed_twice(self):
        """Stop ends the link and invalidates the token; a second stop is harmless."""
        body = self.start().json()
        self.assertEqual(self.client.post(STOP).status_code, 200)
        self.assertEqual(self.client.post(STOP).status_code, 200)
        self.assertIsNotNone(Session.objects.get(pk=body["session_id"]).ended_at)
        post = self.device_client(body["device_token"]).post(
            f"/api/sessions/{body['session_id']}/telemetry/", [self.reading(body["zones"]["Hairpin"])], format="json")
        self.assertIn(post.status_code, (401, 403, 409))

    def test_a_new_link_replaces_the_old_one_and_its_token_stops_working(self):
        """Starting again closes the first session; only the new token works."""
        first, second = self.start().json(), self.start().json()
        self.assertIsNotNone(Session.objects.get(pk=first["session_id"]).ended_at)
        old = self.device_client(first["device_token"]).post(
            f"/api/sessions/{second['session_id']}/telemetry/", [self.reading(second["zones"]["Hairpin"])], format="json")
        self.assertIn(old.status_code, (401, 403))
        new = self.device_client(second["device_token"]).post(
            f"/api/sessions/{second['session_id']}/telemetry/", [self.reading(second["zones"]["Hairpin"])], format="json")
        self.assertEqual(new.status_code, 201)
        self.assertEqual(Telemetry.objects.filter(session_id=first["session_id"]).count(), 0)

    def test_bad_drivers_are_refused_with_a_clear_message(self):
        """A coach, a missing id and a deactivated driver are 400; a driver holding another kart unit is 409."""
        self.assertEqual(self.client.post(START, {"driver_id": str(self.coach.id)}, format="json").status_code, 400)
        self.assertEqual(self.client.post(START, {}, format="json").status_code, 400)
        User.objects.filter(pk=self.driver.pk).update(is_active=False)
        self.assertEqual(self.start().status_code, 400)
        User.objects.filter(pk=self.driver.pk).update(is_active=True)
        Device.objects.create(name="Real kart", device_type=Device.DeviceType.KART_UNIT, assigned_to=self.driver)
        self.assertEqual(self.start().status_code, 409)
