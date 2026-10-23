"""
Trackside — Private API answers are never stored, and the page carries a strict content policy.
"""

import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from config.spa import spa

User = get_user_model()


class TestApiAnswersAreNotStored(APITestCase):
    """Every /api/ answer says no-store and varies by cookie, so a shared browser cannot mix accounts up."""

    def check_private(self, response):
        """The answer must be no-store, private and vary on the cookie."""
        control = response.headers["Cache-Control"]
        self.assertIn("no-store", control)
        self.assertIn("private", control)
        self.assertIn("Cookie", response.headers["Vary"])

    def test_signed_in_answer_is_private(self):
        """/api/auth/me/ for a signed-in driver is not to be stored."""
        driver = User.objects.create_user(email="cache_driver@trackside.local", name="Cache Driver",
                                          role="driver", password="Password123!")
        self.client.force_authenticate(driver)
        self.check_private(self.client.get("/api/auth/me/"))

    def test_refusals_and_public_answers_are_private_too(self):
        """A refused request and the csrf answer are also not to be stored."""
        self.check_private(self.client.get("/api/auth/me/"))
        self.check_private(self.client.get("/api/auth/csrf/"))
        self.check_private(self.client.post("/api/auth/login/", {"identifier": "x", "password": "y"}, format="json"))

    def test_the_health_check_is_not_touched(self):
        """The platform's health check is answered before the middleware and keeps working."""
        self.assertEqual(self.client.get("/api/health/").status_code, 200)


class TestPageContentPolicy(SimpleTestCase):
    """The built page is served with a content policy that allows only its own files and fonts."""

    def serve(self, path="", secure=False):
        """Serve the built page from a temporary folder holding index.html and one hashed asset."""
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "assets"))
            for name in ("index.html", os.path.join("assets", "app-1.js")):
                with open(os.path.join(root, name), "w", encoding="utf-8") as handle:
                    handle.write("x")
            with override_settings(FRONTEND_DIST=root, ALLOWED_HOSTS=["trackside.test"]):
                request = RequestFactory().get(path or "/", secure=secure, HTTP_HOST="trackside.test")
                response = spa(request, path)
                response.close()
                return response

    def test_page_has_the_policy(self):
        """index.html (also for a deep link such as /coach) carries it, and framing is refused."""
        for path in ("", "coach"):
            policy = self.serve(path).headers["Content-Security-Policy"]
            self.assertIn("default-src 'self'", policy)
            self.assertIn("script-src 'self'", policy)
            self.assertNotIn("'unsafe-eval'", policy)
            self.assertNotIn("script-src 'self' 'unsafe-inline'", policy)
            self.assertIn("frame-ancestors 'none'", policy)
            self.assertIn("object-src 'none'", policy)
            self.assertEqual(self.serve(path).headers["Cache-Control"], "no-cache")

    def test_socket_address_follows_the_connection(self):
        """Live feed sockets are allowed to this host only: wss on https, ws on plain http."""
        self.assertIn("wss://trackside.test", self.serve(secure=True).headers["Content-Security-Policy"])
        self.assertIn("ws://trackside.test", self.serve(secure=False).headers["Content-Security-Policy"])

    def test_assets_are_cached_and_have_no_page_policy(self):
        """A hashed asset keeps its long cache and does not get the page policy."""
        response = self.serve("assets/app-1.js")
        self.assertIn("immutable", response.headers["Cache-Control"])
        self.assertNotIn("Content-Security-Policy", response.headers)
