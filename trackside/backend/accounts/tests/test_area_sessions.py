"""
Trackside — One sign-in per role area: a driver tab and a coach tab can both stay signed in in one browser.

The test client keeps ONE cookie jar, like a browser: every request below shares it, and only the
X-Trackside-Area header says which area a request belongs to.
"""

import json

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TransactionTestCase
from django.utils import timezone

from config.asgi import application
from driving_sessions.models import Session
from tracks.models import Track

User = get_user_model()
AUTO = {"HTTP_X_TRACKSIDE_AREA": "auto"}


def area(name):
    """The request header that puts a request into one role area."""
    return {"HTTP_X_TRACKSIDE_AREA": name}


class AreaSessionBase(TransactionTestCase):

    def setUp(self):
        self.driver = User.objects.create_user(email="area_drv@t.test", name="Dee Driver", role="driver", password="DriverPass123!")
        self.coach = User.objects.create_user(email="area_coach@t.test", name="Cole Coach", role="coach", password="CoachPass123!")
        self.browser = Client()   # one cookie jar for everything below

    def sign_in(self, email, password, **extra):
        """POST the login the way the page does (the login limit is cleared first: this test signs in often)."""
        cache.clear()
        return self.browser.post("/api/auth/login/", json.dumps({"identifier": email, "password": password}),
                                 content_type="application/json", **extra)

    def who(self, area_name=None):
        """The /me answer for a request in the given area (or with no area at all)."""
        extra = area(area_name) if area_name else {}
        return self.browser.get("/api/auth/me/", **extra)


class TestTwoRolesInOneBrowser(AreaSessionBase):

    def test_each_login_goes_into_its_own_role_cookie(self):
        """Signing in with "auto" sets sessionid_<role>, and not the old shared sessionid."""
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        self.assertIn("sessionid_driver", self.browser.cookies)
        self.assertIn("sessionid_coach", self.browser.cookies)
        self.assertNotIn("sessionid", self.browser.cookies)

    def test_both_stay_signed_in_and_each_area_sees_only_its_own_user(self):
        """After driver then coach sign in, the driver area is still the driver and the coach area the coach."""
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        self.assertEqual(self.who("driver").json()["role"], "driver")
        self.assertEqual(self.who("coach").json()["role"], "coach")
        self.assertEqual(self.who("driver").json()["name"], "Dee Driver")

    def test_an_area_with_no_sign_in_is_anonymous_even_when_others_are_signed_in(self):
        """Only the coach signed in: the driver area and the admin area stay signed out."""
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        self.assertEqual(self.who("coach").status_code, 200)
        self.assertEqual(self.who("driver").status_code, 403)
        self.assertEqual(self.who("admin").status_code, 403)
        self.assertEqual(self.who().status_code, 403)       # and the old single cookie has nothing

    def test_a_driver_area_can_never_act_as_the_coach(self):
        """With a coach signed in elsewhere in the same browser, driver-area requests still get driver rights only."""
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        for url in ("/api/auth/users/", "/api/devices/", "/api/sessions/roster-status/"):
            response = self.browser.get(url, **area("driver"))
            ok_for_driver = url.endswith("roster-status/")      # a driver may read their own roster entry
            self.assertEqual(response.status_code == 200, ok_for_driver, url)
        roster = self.browser.get("/api/sessions/roster-status/", **area("driver")).json()["roster"]
        self.assertEqual([r["driver_name"] for r in roster], ["Dee Driver"])

    def test_signing_out_of_one_area_leaves_the_other_signed_in(self):
        """Logging the driver out does not log the coach out."""
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        self.assertEqual(self.browser.post("/api/auth/logout/", **area("driver")).status_code, 200)
        self.assertEqual(self.who("driver").status_code, 403)
        self.assertEqual(self.who("coach").json()["role"], "coach")

    def test_signing_in_again_in_one_area_does_not_touch_the_other(self):
        """A second coach sign-in replaces the coach session only; the driver session is untouched."""
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        before = self.browser.cookies["sessionid_driver"].value
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        self.assertEqual(self.browser.cookies["sessionid_driver"].value, before)
        self.assertEqual(self.who("driver").json()["role"], "driver")


class TestLoginRules(AreaSessionBase):

    def test_a_wrong_password_sets_and_deletes_no_cookie(self):
        """A failed sign-in changes nothing: an existing driver sign-in survives a failed coach attempt."""
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        before = self.browser.cookies["sessionid_driver"].value
        response = self.sign_in("area_coach@t.test", "Wrong123!", **AUTO)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.browser.cookies["sessionid_driver"].value, before)
        self.assertNotIn("sessionid_coach", self.browser.cookies)
        self.assertEqual(self.who("driver").json()["role"], "driver")

    def test_naming_the_wrong_area_at_sign_in_is_refused(self):
        """A coach cannot sign in while naming the driver area (and nothing is set)."""
        response = self.sign_in("area_coach@t.test", "CoachPass123!", **area("driver"))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("sessionid_driver", self.browser.cookies)
        self.assertNotIn("sessionid_coach", self.browser.cookies)

    def test_naming_the_right_area_at_sign_in_works(self):
        """Naming the account's own area is accepted."""
        self.assertEqual(self.sign_in("area_coach@t.test", "CoachPass123!", **area("coach")).status_code, 200)
        self.assertEqual(self.who("coach").json()["role"], "coach")

    def test_the_old_single_cookie_flow_is_unchanged(self):
        """No area header at all: the old sessionid cookie is used, as before."""
        self.assertEqual(self.sign_in("area_coach@t.test", "CoachPass123!").status_code, 200)
        self.assertIn("sessionid", self.browser.cookies)
        self.assertEqual(self.who().json()["role"], "coach")
        self.assertEqual(self.who("coach").status_code, 403)    # the old cookie does not leak into an area

    def test_an_unknown_area_value_gets_no_special_access(self):
        """Made-up area names read the old cookie only (nothing, here) and cannot be used to pick another cookie."""
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)
        for fake in ("root", "coach/../x", "driver; admin", ""):
            self.assertEqual(self.browser.get("/api/auth/me/", HTTP_X_TRACKSIDE_AREA=fake).status_code, 403, fake)

    def test_cookie_attributes_are_kept(self):
        """The role cookies are HttpOnly and SameSite=Lax like the old one."""
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        morsel = self.browser.cookies["sessionid_driver"]
        self.assertTrue(morsel["httponly"])
        self.assertEqual(morsel["samesite"], "Lax")


class TestLiveFeedUsesTheAreaCookie(AreaSessionBase):

    def setUp(self):
        super().setUp()
        self.track = Track.objects.create(name="Area Track", created_by=self.coach)
        self.session = Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now())
        self.sign_in("area_drv@t.test", "DriverPass123!", **AUTO)
        self.sign_in("area_coach@t.test", "CoachPass123!", **AUTO)

    def cookie_header(self):
        """The Cookie header a browser holding both sign-ins would send."""
        return "; ".join(f"{name}={morsel.value}" for name, morsel in self.browser.cookies.items()).encode()

    def connect(self, query):
        """Open the live feed of the driver's session; returns (connected, close_code)."""
        async def run():
            communicator = WebsocketCommunicator(
                application, f"/ws/sessions/{self.session.id}/telemetry/{query}",
                headers=[(b"host", b"localhost"), (b"origin", b"http://localhost"), (b"cookie", self.cookie_header())])
            result = await communicator.connect()
            await communicator.disconnect()
            return result
        return async_to_sync(run)()

    def test_the_driver_area_connects_as_the_driver_owner(self):
        """?area=driver uses the driver's cookie: the owner of the session is let in."""
        self.assertEqual(self.connect("?area=driver"), (True, None))

    def test_the_coach_area_connects_as_the_coach(self):
        """?area=coach uses the coach's cookie: a coach may watch any session."""
        self.assertEqual(self.connect("?area=coach"), (True, None))

    def test_an_area_with_no_sign_in_is_refused(self):
        """?area=admin has no cookie, and the other cookies are hidden from it: refused with 4401."""
        self.assertEqual(self.connect("?area=admin"), (False, 4401))

    def test_no_area_and_only_area_cookies_is_refused(self):
        """Without ?area the old single cookie is read, and there is none: refused."""
        self.assertEqual(self.connect(""), (False, 4401))
