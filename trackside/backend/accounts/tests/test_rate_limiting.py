"""
Trackside — Rate limiting test (requirement #9).

Verifies that the login endpoint returns 429 after exceeding
the rate limit of 5 attempts per minute.
"""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRateLimiting:
    """Login endpoint must enforce rate limiting."""

    @pytest.fixture(autouse=True)
    def setup(self):
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
