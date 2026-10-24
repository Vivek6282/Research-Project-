"""
Trackside — Secret handling: production key checks and the first admin's password.
"""

import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from config.secret_checks import check_production_secret_key

User = get_user_model()


class TestProductionSecretKey(SimpleTestCase):
    """Copied example keys, short keys and repetitive keys never start production."""

    def test_example_and_weak_keys_are_refused(self):
        """Every placeholder from the example files, plus empty, short and repetitive keys."""
        for key in ("", "replace-me-with-a-long-random-value", "change-this-to-a-secure-random-secret-key-in-production",
                    "dev-secret-key-trackside-local-1234567890-secure-key", "generate-a-strong-random-django-secret-key-here",
                    "django-insecure-abcdefghijklmnopqrstuvwxyz0123456789", "short-but-random-Xy7", "a" * 60):
            with self.assertRaises(ImproperlyConfigured, msg=key):
                check_production_secret_key(key)

    def test_a_generated_key_is_accepted(self):
        """A Render-length (44) or secrets.token_urlsafe(50) key passes."""
        check_production_secret_key("q3Yv8ZsW0kP2nR7tL1xC9bH4mJ6dF5gA0eU3iO8yT2w=")
        check_production_secret_key("hV1n0qkR3Zt8Lw9yP2sX5cB7mD4fG6jA1eU0iO3yT2wQ8rS5vN7bM9kL4pH6gJ2d")


class TestSeedAdminPassword(TestCase):
    """The first admin cannot be created with a weak password."""

    def seed(self, password):
        """Run seed_admin with this password."""
        env = {"ADMIN_EMAIL": "first_admin@t.local", "ADMIN_NAME": "First Admin", "ADMIN_PASSWORD": password}
        with mock.patch.dict(os.environ, env):
            call_command("seed_admin", stdout=open(os.devnull, "w"))

    def test_weak_password_is_refused_and_no_account_is_made(self):
        """'password123' stops the command; nothing is created."""
        with self.assertRaises(CommandError):
            self.seed("password123")
        self.assertFalse(User.objects.filter(email="first_admin@t.local").exists())

    def test_strong_password_creates_the_admin(self):
        """A long, uncommon password creates the admin."""
        self.seed("Hairpin-Brake-Marker-2026!")
        self.assertTrue(User.objects.filter(email="first_admin@t.local", role="admin").exists())
