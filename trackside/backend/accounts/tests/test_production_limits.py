"""
Trackside — Production-only trust rules and the request size limit.
"""

import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from config.limits import MAX_REQUEST_BYTES


class TestProductionTrustsOnlyItsOwnOrigins(SimpleTestCase):

    def origins_in(self, django_env):
        """The CORS and CSRF trusted origins a server started with this DJANGO_ENV ends up with."""
        code = (
            "import os, django\n"
            "os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'\n"
            "django.setup()\n"
            "from django.conf import settings\n"
            "print('|'.join(settings.CORS_ALLOWED_ORIGINS + settings.CSRF_TRUSTED_ORIGINS))\n"
        )
        env = dict(os.environ, DJANGO_ENV=django_env, DEBUG="False", SECRET_KEY="a-long-production-style-key-0123456789",
                   CORS_ALLOWED_ORIGINS="https://trackside.example.com", DB_ENGINE="postgresql",
                   DATABASE_URL="postgres://u:p@localhost:5432/db", ALLOWED_HOSTS="trackside.example.com")
        done = subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr[-600:])
        return done.stdout.strip().splitlines()[-1]

    def test_production_has_no_localhost_origins(self):
        """In production only the configured https origin is trusted, with no http://localhost development address."""
        origins = self.origins_in("production")
        self.assertIn("https://trackside.example.com", origins)
        self.assertNotIn("localhost", origins)
        self.assertNotIn("127.0.0.1", origins)

    def test_development_still_trusts_the_local_frontend(self):
        """In development the local frontend addresses are still allowed, so local work is not broken."""
        self.assertIn("http://localhost:5173", self.origins_in("development"))


class TestRequestSizeLimit(SimpleTestCase):

    def test_an_oversized_request_is_refused_before_it_is_read(self):
        """A body declared larger than the limit gets 413."""
        response = APIClient().post("/api/auth/login/", "{}", content_type="application/json",
                                    CONTENT_LENGTH=str(MAX_REQUEST_BYTES + 1))
        self.assertEqual(response.status_code, 413)

    def test_a_normal_request_is_not_affected(self):
        """A small request reaches the view (an empty login is a 400 from the form check)."""
        self.assertEqual(APIClient().post("/api/auth/login/", {}, format="json").status_code, 400)
