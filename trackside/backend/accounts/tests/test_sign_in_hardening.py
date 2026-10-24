"""
Trackside — Sign-in hardening: lockout, security log and password rules.
"""

import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from accounts.login_guard import LOCKED_MESSAGE, MAX_FAILED_SIGN_INS
from accounts.models import AuditLogEntry

User = get_user_model()
LOGIN = "/api/auth/login/"
GOOD_PASSWORD = "Kerb-Apex-Line-2026!"
LOOSE_LIMITS = {"LOGIN_THROTTLE_RATE": "1000/min", "LOGIN_ACCOUNT_THROTTLE_RATE": "1000/min"}


@mock.patch.dict(os.environ, LOOSE_LIMITS)
class TestLockout(APITestCase):
    """Ten wrong passwords lock sign-in for that account for 15 minutes, without revealing which accounts exist."""

    def setUp(self):
        """A driver with an email, a username and a short driver ID; the per-minute limits are relaxed."""
        cache.clear()
        self.driver = User.objects.create_user(email="lock@t.local", name="Lock Driver", password=GOOD_PASSWORD,
                                               role="driver", username="TRK-DRV-009001", driver_code="D90001")

    def sign_in(self, identifier, password):
        """POST the login form."""
        return self.client.post(LOGIN, {"identifier": identifier, "password": password}, format="json")

    def fail(self, identifier, times):
        """Send that many wrong passwords."""
        for _ in range(times):
            self.assertEqual(self.sign_in(identifier, "wrong-password").status_code, 401)

    def test_right_password_is_refused_once_locked(self):
        """After the limit even the correct password gets 429 with the lockout message."""
        self.fail("lock@t.local", MAX_FAILED_SIGN_INS)
        response = self.sign_in("lock@t.local", GOOD_PASSWORD)
        self.assertEqual((response.status_code, response.json()["detail"]), (429, LOCKED_MESSAGE))

    def test_email_username_and_driver_id_share_one_counter(self):
        """Spreading guesses over the three ways to name the account does not give more guesses."""
        self.fail("lock@t.local", 4)
        self.fail("TRK-DRV-009001", 3)
        self.fail("D90001", 3)
        self.assertEqual(self.sign_in("lock@t.local", GOOD_PASSWORD).status_code, 429)

    def test_unknown_account_locks_the_same_way(self):
        """Same status and message for a made-up identifier, so lockout does not reveal accounts."""
        self.fail("nobody@t.local", MAX_FAILED_SIGN_INS)
        unknown = self.sign_in("nobody@t.local", "anything")
        self.fail("lock@t.local", MAX_FAILED_SIGN_INS)
        known = self.sign_in("lock@t.local", "anything")
        self.assertEqual((unknown.status_code, unknown.json()), (known.status_code, known.json()))

    def test_success_resets_the_counter(self):
        """Nine failures, one success, then nine more failures: still not locked."""
        self.fail("lock@t.local", MAX_FAILED_SIGN_INS - 1)
        self.assertEqual(self.sign_in("lock@t.local", GOOD_PASSWORD).status_code, 200)
        self.client.logout()
        self.fail("lock@t.local", MAX_FAILED_SIGN_INS - 1)
        self.assertEqual(self.sign_in("lock@t.local", GOOD_PASSWORD).status_code, 200)

    def test_lockout_of_a_real_account_is_written_to_the_audit_log_once(self):
        """One SIGN_IN_LOCKED entry naming the account; none for unknown identifiers."""
        self.fail("lock@t.local", MAX_FAILED_SIGN_INS)
        self.fail("nobody@t.local", MAX_FAILED_SIGN_INS)
        entries = AuditLogEntry.objects.filter(action="SIGN_IN_LOCKED")
        self.assertEqual([e.target_user_id for e in entries], [str(self.driver.id)])

    def test_security_log_has_events_but_never_the_password(self):
        """Failure, success and logout are logged with the account id; the typed password never appears."""
        with self.assertLogs("trackside.security", level="INFO") as captured:
            self.sign_in("lock@t.local", "my-secret-typo")
            self.sign_in("nobody@t.local", "another-secret")
            self.sign_in("lock@t.local", GOOD_PASSWORD)
            self.client.post("/api/auth/logout/")
        text = "\n".join(captured.output)
        for event in ("auth.login_failed", "auth.login_ok", "auth.logout", f"user={self.driver.pk}"):
            self.assertIn(event, text)
        for secret in ("my-secret-typo", "another-secret", GOOD_PASSWORD, "nobody@t.local"):
            self.assertNotIn(secret, text)

    def test_oversized_login_fields_are_refused(self):
        """A 300-character password or identifier is a 400, not hashed."""
        self.assertEqual(self.sign_in("lock@t.local", "x" * 300).status_code, 400)
        self.assertEqual(self.sign_in("a" * 300, GOOD_PASSWORD).status_code, 400)


class TestPasswordRules(APITestCase):
    """The admin cannot give an account a weak password."""

    def setUp(self):
        """An admin and a driver to edit."""
        self.admin = User.objects.create_user(email="pw_admin@t.local", name="Pw Admin", password=GOOD_PASSWORD, role="admin")
        self.driver = User.objects.create_user(email="pw_driver@t.local", name="Marco Ferretti", password=GOOD_PASSWORD, role="driver")
        self.client.force_authenticate(self.admin)

    def create(self, password, name="New Driver"):
        """Create a driver with this password."""
        return self.client.post("/api/auth/users/", {"name": name, "role": "driver", "password": password}, format="json")

    def test_weak_passwords_are_refused_with_the_reason(self):
        """Too short, too common, all numbers, or too close to the name: 400 on the password field."""
        for password, name in (("Ab1!", "New Driver"), ("password123", "New Driver"), ("8263749152", "New Driver"),
                               ("marcoferretti", "Marco Ferretti")):
            response = self.create(password, name)
            self.assertEqual(response.status_code, 400, password)
            self.assertIn("password", response.json())

    def test_strong_password_is_accepted(self):
        """A long, uncommon password creates the account."""
        self.assertEqual(self.create(GOOD_PASSWORD).status_code, 201)

    def test_changing_to_a_weak_password_is_refused(self):
        """The edit form runs the same rules; leaving the password out still works."""
        url = f"/api/auth/users/{self.driver.id}/"
        self.assertEqual(self.client.patch(url, {"password": "password123"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"name": "Marco F."}, format="json").status_code, 200)
