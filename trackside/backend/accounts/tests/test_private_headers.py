"""
Trackside — Private API answers are never stored, and the page carries a strict content policy.
"""

import os
import subprocess
import sys
import tempfile

from django.conf import settings
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


class TestMapPicturesAndReferrer(SimpleTestCase):
    """The page may load map pictures from the configured tile host only, and tile servers see the site's address."""

    def policy(self):
        """The Content-Security-Policy of the built page."""
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as handle:
                handle.write("x")
            with override_settings(FRONTEND_DIST=root, ALLOWED_HOSTS=["trackside.test"]):
                response = spa(RequestFactory().get("/", HTTP_HOST="trackside.test"), "")
                response.close()
                return response.headers["Content-Security-Policy"]

    def test_images_come_from_the_site_data_urls_and_the_tile_host_only(self):
        """img-src lists the OpenStreetMap tile host and no wildcard; scripts still come from the site alone."""
        policy = self.policy()
        self.assertIn("img-src 'self' data: blob: https://tile.openstreetmap.org;", policy)
        self.assertNotIn("img-src *", policy)
        self.assertIn("script-src 'self';", policy)

    def test_another_tile_host_can_be_configured(self):
        """MAP_TILE_HOSTS changes the allowed host (for satellite pictures), still https only."""
        with override_settings(MAP_TILE_HOSTS=["https://api.maptiler.com"]):
            policy = self.policy()
        self.assertIn("img-src 'self' data: blob: https://api.maptiler.com;", policy)
        self.assertNotIn("tile.openstreetmap.org", policy)

    def test_bad_tile_hosts_stop_the_server_from_starting(self):
        """A host with a path, a space, a semicolon or plain http would loosen the policy, so settings refuse it."""
        code = "import os, django; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup(); print('started')"
        for bad in ("http://tile.example.com", "https://x.com; script-src *", "https://x.com/path", "https://x.com img-src *", "*"):
            done = subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR, capture_output=True, text=True,
                                  env=dict(os.environ, MAP_TILE_HOSTS=bad), timeout=120)
            self.assertNotEqual(done.returncode, 0, bad)
            self.assertNotIn("started", done.stdout, bad)

    def test_the_site_sends_its_address_but_never_a_page_path_to_other_sites(self):
        """Referrer-Policy is strict-origin-when-cross-origin: tile servers get the origin only."""
        response = APITestCase.client_class().get("/api/auth/csrf/")
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
