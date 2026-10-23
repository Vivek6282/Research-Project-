"""
Trackside — Rate limiting test (requirement #9).

Verifies that the login endpoint returns 429 after exceeding
the rate limit of 5 attempts per minute.
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRateLimiting(TestCase):
    """Login endpoint must enforce rate limiting."""

    def setUp(self):
        """Create a test user and clear any existing throttle state."""
        self.client = APIClient()

        # Clear Django's default cache to reset throttle counters
        from django.core.cache import cache
        cache.clear()

        User.objects.create_user(
            email="ratelimit@test.local",
            name="Rate Limit Test",
            role="driver",
            password="TestPass123!",
        )

    def test_login_rate_limit_returns_429(self):
        """
        The 6th rapid login attempt must return HTTP 429.
        Rate limit: 5/min configured in settings.
        """
        login_data = {
            "email": "ratelimit@test.local",
            "password": "WrongPassword!",
        }

        # First 5 attempts should return 401 (wrong password)
        for i in range(5):
            response = self.client.post(
                "/api/auth/login/",
                login_data,
                format="json",
            )
            assert response.status_code == 401, (
                f"Attempt {i + 1}: expected 401, got {response.status_code}"
            )

        # 6th attempt should be rate-limited
        response = self.client.post(
            "/api/auth/login/",
            login_data,
            format="json",
        )
        assert response.status_code == 429, (
            f"Expected 429 on 6th attempt, got {response.status_code}"
        )


@pytest.mark.django_db
class TestPerAccountLoginLimit(TestCase):
    """Guesses against one account are capped whatever address they come from."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        User.objects.create_user(email="acct@test.local", name="Acct", role="driver", password="TestPass123!")

    def attempt(self, who, address):
        """One wrong login for the identifier from the given address."""
        return self.client.post("/api/auth/login/", {"identifier": who, "password": "Wrong123!"},
                                format="json", REMOTE_ADDR=address).status_code

    def test_many_addresses_cannot_dodge_the_account_limit(self):
        """Ten wrong tries from ten different addresses are answered 401; the 11th, from a new address, is 429."""
        for n in range(10):
            self.assertEqual(self.attempt("acct@test.local", f"10.0.0.{n + 1}"), 401)
        self.assertEqual(self.attempt("acct@test.local", "10.0.0.99"), 429)

    def test_the_limit_ignores_letter_case_and_spaces(self):
        """The same account typed differently shares one counter."""
        for n in range(10):
            self.attempt(("ACCT@test.local", " acct@test.local ", "Acct@Test.local")[n % 3], f"10.0.1.{n + 1}")
        self.assertEqual(self.attempt("acct@test.local", "10.0.1.99"), 429)

    def test_other_accounts_are_not_affected(self):
        """Someone else signing in is not slowed down by guesses against this account."""
        User.objects.create_user(email="other@test.local", name="Other", role="driver", password="TestPass123!")
        for n in range(11):
            self.attempt("acct@test.local", f"10.0.2.{n + 1}")
        ok = self.client.post("/api/auth/login/", {"identifier": "other@test.local", "password": "TestPass123!"},
                              format="json", REMOTE_ADDR="10.0.2.200")
        self.assertEqual(ok.status_code, 200)

    def test_an_empty_identifier_gets_a_normal_validation_error(self):
        """No identifier typed: a 400 from the form check, not a throttle error."""
        res = self.client.post("/api/auth/login/", {"password": "x"}, format="json")
        self.assertEqual(res.status_code, 400)


@pytest.mark.django_db
class TestAdminSeesItsOwnAddress(TestCase):
    """The admin screen shows how the server reads the admin's address, and only admins can see it."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(email="addr_admin@test.local", name="Addr Admin", role="admin", password="TestPass123!")
        self.coach = User.objects.create_user(email="addr_coach@test.local", name="Addr Coach", role="coach", password="TestPass123!")

    def test_admin_gets_the_address_facts(self):
        """The answer names the address, the number of forwarded entries and the trusted proxy count."""
        self.client.force_authenticate(self.admin)
        data = self.client.get("/api/auth/diagnostics/", REMOTE_ADDR="203.0.113.7").json()
        self.assertEqual(data["client_address_seen"], "203.0.113.7")
        self.assertEqual(data["forwarded_for_entries"], 0)
        self.assertIn("trusted_proxy_count", data)

    def test_forwarded_entries_are_counted(self):
        """Two entries in X-Forwarded-For are reported as two."""
        self.client.force_authenticate(self.admin)
        data = self.client.get("/api/auth/diagnostics/", HTTP_X_FORWARDED_FOR="198.51.100.1, 10.0.0.2").json()
        self.assertEqual(data["forwarded_for_entries"], 2)

    def test_a_coach_is_refused(self):
        """Coaches cannot read it."""
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.get("/api/auth/diagnostics/").status_code, 403)
