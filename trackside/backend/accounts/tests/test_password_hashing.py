"""
Trackside — Password hashing test (requirement #8).

Verifies that passwords are stored using Django's PBKDF2-SHA256 hasher,
never in plain text, and that the stored hash follows the expected format.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestPasswordHashing:
    """Ensure passwords are hashed via PBKDF2, never stored or logged raw."""

    def test_password_is_hashed_with_pbkdf2(self):
        """Stored password field starts with 'pbkdf2_sha256$', not plaintext."""
        user = User.objects.create_user(
            email="hashtest@trackside.local",
            name="Hash Test",
            role="driver",
            password="TestPassword123!",
        )
        # The stored password must be a PBKDF2 hash, not the raw password
        assert user.password.startswith("pbkdf2_sha256$"), (
            f"Expected PBKDF2 hash, got: {user.password[:30]}..."
        )
        assert user.password != "TestPassword123!", (
            "Password was stored in plain text — this is a critical security violation"
        )

    def test_password_verification_works(self):
        """check_password() correctly validates the raw password against the hash."""
        user = User.objects.create_user(
            email="checktest@trackside.local",
            name="Check Test",
            role="driver",
            password="CorrectPassword1!",
        )
        assert user.check_password("CorrectPassword1!")
        assert not user.check_password("WrongPassword!")

    def test_different_users_have_different_hashes(self):
        """Even with the same password, each user gets a unique salt/hash."""
        user1 = User.objects.create_user(
            email="user1@trackside.local",
            name="User One",
            role="driver",
            password="SamePassword123!",
        )
        user2 = User.objects.create_user(
            email="user2@trackside.local",
            name="User Two",
            role="driver",
            password="SamePassword123!",
        )
        assert user1.password != user2.password, (
            "Two users with the same password have the same hash — salt is missing"
        )
