"""
Trackside — Access sweep: every route is tried with every method by the wrong people.

Not one hand-picked case: the routes come from the URL table, so a route added later is covered too.
A request is "refused" when the answer is 401, 403 or 404 (404 hides that the thing exists).
"""

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import get_resolver
from django.utils import timezone
from rest_framework.test import APITestCase

from devices.models import Device
from driving_sessions.models import Alert, Session, Telemetry
from tracks.models import Track, Zone

User = get_user_model()

METHODS = ("get", "post", "put", "patch", "delete")
REFUSED = (401, 403, 404, 405)   # 405: the route has no handler for that method, so nothing runs
PUBLIC_ROUTES = {"api/health/", "api/auth/csrf/", "api/auth/login/"}   # open on purpose
ADMIN_ONLY = ("api/auth/users", "api/auth/audit-logs", "api/auth/diagnostics", "api/devices/")
COACH_MAY_READ = ("api/devices/", "api/devices/<uuid:pk>/")   # coaches see device status; only the admin changes it
STAFF_ONLY = ("api/tracks/import/", "api/tracks/draw/", "api/tracks/<uuid:pk>/corners/", "api/tracks/<uuid:pk>/duplicate/",
              "api/tracks/<uuid:pk>/restore/", "api/tracks/<uuid:pk>/survey/", "api/demo/", "api/laptop-link/")
OWN_SESSION_ONLY = "api/sessions/<uuid:"


def route_templates():
    """Every route of the project as a text with <converters> left in, e.g. api/sessions/<uuid:pk>/."""
    found = []

    def walk(patterns, prefix=""):
        for item in patterns:
            text = prefix + str(item.pattern)
            if hasattr(item, "url_patterns"):
                walk(item.url_patterns, text)
            else:
                found.append(text)

    walk(get_resolver().url_patterns)
    return [t for t in found if t.startswith("api/")]


class AccessSweepBase(APITestCase):
    """Five kinds of people and one of everything they might try to reach."""

    def setUp(self):
        make = lambda role, n: User.objects.create_user(
            email=f"{role}{n}@sweep.test", name=f"{role} {n}", role=role, password="SweepPass123!")
        self.admin, self.coach = make("admin", 1), make("coach", 1)
        self.driver_a, self.driver_b = make("driver", 1), make("driver", 2)
        self.track = Track.objects.create(name="Sweep Track", created_by=self.coach)
        self.zone = Zone.objects.create(track=self.track, label="T1", threshold_g=1.2)
        self.session = Session.objects.create(driver=self.driver_a, track=self.track, started_at=timezone.now())
        self.reading = Telemetry.objects.create(session=self.session, zone=self.zone, lateral_g=0.5, speed_kmh=40,
                                                gps_lat=0, gps_lng=0, recorded_at=timezone.now(), lap_number=1)
        self.alert = Alert.objects.create(session=self.session, zone=self.zone, severity=Alert.Severity.RED, g_value=1.3,
                                          threshold_applied=1.2, triggered_at=timezone.now())
        self.device = Device.objects.create(name="Sweep Kart Unit", device_type=Device.DeviceType.KART_UNIT)
        self.ids = {"pk": str(self.track.id), "track_pk": str(self.track.id), "session_pk": str(self.session.id),
                    "driver_pk": str(self.driver_a.id)}

    def fill(self, template):
        """Put real ids into the converters: sessions' routes get the session, device routes the device, and so on."""
        text = template
        if template.startswith("api/sessions/"):
            text = text.replace("<uuid:pk>", str(self.session.id))
        elif template.startswith("api/auth/users/"):
            text = text.replace("<uuid:pk>", str(self.driver_a.id))
        elif template.startswith("api/devices/"):
            text = text.replace("<uuid:pk>", str(self.device.id))
        elif template.startswith("api/tracks/<uuid:track_pk>/zones/"):
            text = text.replace("<uuid:pk>", str(self.zone.id))
        else:
            text = text.replace("<uuid:pk>", str(self.track.id))
        for name in ("track_pk", "session_pk", "driver_pk"):
            text = text.replace(f"<uuid:{name}>", self.ids[name])
        return "/" + text

    def statuses(self, client, template, methods=METHODS):
        """{method: status} for the route with an empty JSON body."""
        url = self.fill(template)
        return {m: getattr(client, m)(url, {}, format="json").status_code for m in methods}

    def assert_refused(self, who, client, templates, empty_list_ok=False):
        """Every method on every template is refused for this person.

        With empty_list_ok a list route may answer 200, but only with no rows at all (the scoped-list way of refusing)."""
        for template in templates:
            for method, code in self.statuses(client, template).items():
                if empty_list_ok and method == "get" and code == 200:
                    body = client.get(self.fill(template)).json()
                    rows = body.get("results", body) if isinstance(body, dict) else body
                    self.assertEqual(rows, [], f"{who} was shown rows by GET /{template}: {rows}")
                    continue
                self.assertIn(code, REFUSED, f"{who} got {code} for {method.upper()} /{template}")


class TestAccessSweep(AccessSweepBase):

    def test_the_sweep_sees_the_routes(self):
        """The URL table is read (a broken reader would make every test below pass for nothing)."""
        templates = route_templates()
        self.assertGreater(len(templates), 40)
        self.assertIn("api/sessions/<uuid:pk>/", templates)

    def test_anonymous_is_refused_everywhere_except_the_public_routes(self):
        """Nobody signed in: every route refuses every method, except health, csrf and login."""
        private = [t for t in route_templates() if t not in PUBLIC_ROUTES]
        self.assert_refused("anonymous", self.client, private)

    def test_a_driver_is_refused_on_admin_and_staff_routes(self):
        """A driver cannot touch user management, devices, imports, surveys, corner edits, demos or laptop links."""
        self.client.force_authenticate(self.driver_b)
        staff = [t for t in route_templates() if t.startswith(ADMIN_ONLY + STAFF_ONLY) and t != "api/tracks/"]
        self.assertGreater(len(staff), 12)
        self.assert_refused("driver", self.client, staff)

    def test_a_coach_is_refused_on_admin_only_routes(self):
        """A coach cannot manage users, read the audit log, run diagnostics, send device commands or change devices."""
        self.client.force_authenticate(self.coach)
        admin_only = [t for t in route_templates() if t.startswith(ADMIN_ONLY) and t not in COACH_MAY_READ]
        self.assertGreater(len(admin_only), 6)
        self.assert_refused("coach", self.client, admin_only)
        for template in COACH_MAY_READ:   # reading is allowed by design; every change is refused
            changes = self.statuses(self.client, template, methods=("post", "put", "patch", "delete"))
            for method, code in changes.items():
                self.assertIn(code, REFUSED, f"coach got {code} for {method.upper()} /{template}")
        self.assertEqual(self.client.get("/api/devices/").status_code, 200)
        self.assertNotIn("api_key_hash", self.client.get("/api/devices/").json().__str__())

    def test_another_driver_cannot_reach_a_session_that_is_not_theirs(self):
        """Driver B gets nothing from driver A's session: not its readings, alerts, notes, corner times or finish."""
        self.client.force_authenticate(self.driver_b)
        own_routes = [t for t in route_templates() if t.startswith(OWN_SESSION_ONLY)]
        self.assertGreater(len(own_routes), 6)
        self.assert_refused("driver B", self.client, own_routes, empty_list_ok=True)

    def test_the_session_owner_is_not_locked_out(self):
        """The owner can still read their own session (the sweep above is not refusing everyone)."""
        self.client.force_authenticate(self.driver_a)
        self.assertEqual(self.client.get(f"/api/sessions/{self.session.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/sessions/{self.session.id}/alerts/").status_code, 200)

    def test_a_driver_sees_only_their_own_session_in_lists(self):
        """Lists are scoped: driver B's session list does not contain driver A's session."""
        self.client.force_authenticate(self.driver_b)
        listed = self.client.get("/api/sessions/").json()
        rows = listed["results"] if isinstance(listed, dict) else listed
        self.assertNotIn(str(self.session.id), [row["id"] for row in rows])

    def test_a_driver_cannot_close_their_own_session_or_create_one_for_another_driver(self):
        """Closing is not for drivers, and a driver cannot start a session in someone else's name."""
        self.client.force_authenticate(self.driver_a)
        self.assertEqual(self.client.post(f"/api/sessions/{self.session.id}/finish/", {}, format="json").status_code, 403)
        made = self.client.post("/api/sessions/", {"driver": str(self.driver_b.id), "track": str(self.track.id)}, format="json")
        self.assertIn(made.status_code, REFUSED + (400,))
        self.assertFalse(Session.objects.filter(driver=self.driver_b).exists())


class TestWrongRoleCannotChangeAccounts(AccessSweepBase):

    def test_a_driver_cannot_promote_themselves(self):
        """A driver changing their own role through any user route is refused and nothing changes."""
        self.client.force_authenticate(self.driver_a)
        for method in ("patch", "put"):
            response = getattr(self.client, method)(f"/api/auth/users/{self.driver_a.id}/", {"role": "admin"}, format="json")
            self.assertIn(response.status_code, REFUSED)
        self.driver_a.refresh_from_db()
        self.assertEqual(self.driver_a.role, "driver")

    def test_me_cannot_be_used_to_change_the_role(self):
        """The 'me' route is read-only for the role: no method turns a driver into something else."""
        self.client.force_authenticate(self.driver_a)
        for method in ("patch", "put", "post"):
            getattr(self.client, method)("/api/auth/me/", {"role": "admin"}, format="json")
        self.driver_a.refresh_from_db()
        self.assertEqual(self.driver_a.role, "driver")


class TestCsrfIsEnforced(AccessSweepBase):

    def test_a_signed_in_post_without_the_csrf_token_is_refused(self):
        """A page on another site cannot make a signed-in browser change things: no token, no change."""
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.coach)
        for url in ("/api/sessions/", "/api/tracks/", "/api/auth/logout/"):
            self.assertEqual(browser.post(url, "{}", content_type="application/json").status_code, 403, url)
        browser.force_login(self.admin)
        self.assertEqual(browser.post("/api/auth/users/", "{}", content_type="application/json").status_code, 403)


class TestWritesToSomeoneElsesSession(AccessSweepBase):

    def test_driver_b_cannot_write_readings_to_driver_a(self):
        """A complete, valid body from driver B is refused for A's session, and nothing is saved."""
        self.client.force_authenticate(self.driver_b)
        now = timezone.now().isoformat()
        reading = {"recorded_at": now, "lateral_g": 0.4, "speed_kmh": 40, "gps_lat": 0, "gps_lng": 0, "lap_number": 1}
        biometric = {"recorded_at": now, "heart_rate": 90, "spo2": 98, "breathing_rate": 15}
        before = (Telemetry.objects.count(), self.session.biometric_readings.count())
        self.assertEqual(self.client.post(f"/api/sessions/{self.session.id}/telemetry/", reading, format="json").status_code, 403)
        self.assertEqual(self.client.post(f"/api/sessions/{self.session.id}/biometrics/", biometric, format="json").status_code, 403)
        self.assertEqual((Telemetry.objects.count(), self.session.biometric_readings.count()), before)

    def test_outsiders_are_refused_before_the_body_is_checked(self):
        """An empty body from driver B gets 403 (not 400), so the validation rules are not open to probing."""
        self.client.force_authenticate(self.driver_b)
        self.assertEqual(self.client.post(f"/api/sessions/{self.session.id}/biometrics/", {}, format="json").status_code, 403)

    def test_the_owner_can_still_write_biometrics(self):
        """Driver A, the owner, still gets through to the normal validation and saving."""
        self.client.force_authenticate(self.driver_a)
        body = {"recorded_at": timezone.now().isoformat(), "heart_rate": 90, "spo2": 98, "breathing_rate": 15}
        self.assertEqual(self.client.post(f"/api/sessions/{self.session.id}/biometrics/", body, format="json").status_code, 201)
