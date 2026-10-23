"""
Trackside — Audit fixes F3 (login timing) and F4 (no admin lockout).
"""

import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class TestLoginDoesTheSamePasswordWork(APITestCase):
    """An unknown account costs the same password work as a known one, so timing does not reveal accounts."""

    def setUp(self):
        cache.clear()
        User.objects.create_user(email="known@t.test", name="Known", role="coach", password="KnownPass123!")

    def test_unknown_account_is_checked_against_the_dummy_hash(self):
        """For an account that does not exist the password check still runs, and the answer is the same 401."""
        with patch("accounts.views_auth.check_password") as spent:
            res = self.client.post("/api/auth/login/", {"identifier": "ghost@t.test", "password": "Whatever123!"}, format="json")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Invalid email/username or password.")
        spent.assert_called_once()

    def test_unknown_account_is_not_answered_instantly(self):
        """The answer takes real hashing time (the unmeasured shortcut was about 3 ms, the real work about 200 ms)."""
        started = time.perf_counter()
        self.client.post("/api/auth/login/", {"identifier": "ghost2@t.test", "password": "Whatever123!"}, format="json")
        self.assertGreater(time.perf_counter() - started, 0.02)

    def test_known_account_wrong_password_gives_the_same_answer(self):
        """The wrong-password answer for a real account is identical to the unknown-account answer."""
        known = self.client.post("/api/auth/login/", {"identifier": "known@t.test", "password": "Wrong123!"}, format="json")
        cache.clear()
        ghost = self.client.post("/api/auth/login/", {"identifier": "ghost3@t.test", "password": "Wrong123!"}, format="json")
        self.assertEqual((known.status_code, known.json()), (ghost.status_code, ghost.json()))

    def test_a_correct_login_still_works(self):
        """The change did not break signing in."""
        res = self.client.post("/api/auth/login/", {"identifier": "known@t.test", "password": "KnownPass123!"}, format="json")
        self.assertEqual(res.status_code, 200)


class TestAdminCannotLockTheSystemOut(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(email="adm1@t.test", name="Admin One", role="admin", password="AdminPass123!")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def patch_user(self, user, body):
        """PATCH a user as the signed-in admin."""
        return self.client.patch(f"/api/auth/users/{user.id}/", body, format="json")

    def test_admin_cannot_change_their_own_role(self):
        """Demoting oneself is refused and the role stays admin."""
        res = self.patch_user(self.admin, {"role": "coach"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("role", res.json())
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "admin")

    def test_admin_still_cannot_deactivate_themselves(self):
        """The existing rule still holds."""
        self.assertEqual(self.patch_user(self.admin, {"is_active": False}).status_code, 400)

    def test_saving_ones_own_unchanged_role_is_fine(self):
        """Sending the same role back (as an edit form does) is not a change."""
        self.assertEqual(self.patch_user(self.admin, {"role": "admin", "name": "Admin One Renamed"}).status_code, 200)

    def test_another_admin_can_be_demoted_while_one_remains(self):
        """With a second admin the caller stays, so demoting or deactivating the other one is allowed."""
        other = User.objects.create_user(email="adm2@t.test", name="Admin Two", role="admin", password="AdminPass123!")
        self.assertEqual(self.patch_user(other, {"is_active": False}).status_code, 200)
        other.refresh_from_db()
        self.assertFalse(other.is_active)

    def test_the_last_active_admin_cannot_be_removed_by_any_path(self):
        """Even when the caller is not that admin (for example a race), the last active admin is protected."""
        from accounts.serializers import UserUpdateSerializer

        class FakeRequest:
            user = User(id="00000000-0000-0000-0000-000000000001")
        serializer = UserUpdateSerializer(self.admin, data={"role": "coach"}, partial=True, context={"request": FakeRequest()})
        self.assertFalse(serializer.is_valid())
        self.assertIn("last active admin", str(serializer.errors))

    def test_other_roles_can_still_be_edited_freely(self):
        """Editing a coach or driver is unaffected."""
        coach = User.objects.create_user(email="c1@t.test", name="Coach One", role="coach", password="CoachPass123!")
        self.assertEqual(self.patch_user(coach, {"name": "Coach Renamed"}).status_code, 200)
