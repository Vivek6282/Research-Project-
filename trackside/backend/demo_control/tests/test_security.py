"""
Trackside — Demo Control security rules (R1-R3).

Rule 1: 404 when DEMO_TOOLS_ENABLED is not 'true'.
Rule 2: 403 when DJANGO_ENV is 'production'.
Rule 3: 403 for admin, driver and device; 401/403 for anonymous; coach allowed.
(Rules 4-6 are covered in test_demo_run.py.)
"""

import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from demo_control.simulator import reset_state_for_testing

User = get_user_model()
DEV = {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}
START, STOP, STATUS = "/api/demo/simulator/start/", "/api/demo/simulator/stop/", "/api/demo/simulator/status/"


class DemoControlSecurityTests(APITestCase):
    """The same gates apply to start, stop and status."""

    def setUp(self):
        """Create one user per role and clear the simulator state."""
        super().setUp()
        reset_state_for_testing()
        self.addCleanup(reset_state_for_testing)
        make = User.objects.create_user
        self.coach = make(email="sec_coach@trackside.local", name="Coach", role="coach", password="Password123!")
        self.admin = make(email="sec_admin@trackside.local", name="Admin", role="admin", password="Password123!")
        self.driver = make(email="sec_driver@trackside.local", name="Driver", role="driver", password="Password123!")

    def all_three(self):
        """Status codes of start, stop and status for the current client."""
        return (self.client.post(START, {}, format="json").status_code,
                self.client.post(STOP, format="json").status_code,
                self.client.get(STATUS).status_code)

    def test_rule_1_off_when_demo_tools_disabled_returns_404(self):
        """When DEMO_TOOLS_ENABLED is false, empty or unset every endpoint answers 404."""
        self.client.force_authenticate(self.coach)
        for env_val in ["false", "0", "", None]:
            env_patch = {} if env_val is None else {"DEMO_TOOLS_ENABLED": env_val}
            with patch.dict(os.environ, env_patch, clear=False):
                if env_val is None:
                    os.environ.pop("DEMO_TOOLS_ENABLED", None)
                self.assertEqual(self.all_three(), (404, 404, 404), f"DEMO_TOOLS_ENABLED={env_val!r}")

    def test_rule_2_refuse_when_production_returns_403(self):
        """Even a coach gets 403 everywhere when DJANGO_ENV is production."""
        self.client.force_authenticate(self.coach)
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "production"}):
            self.assertEqual(self.all_three(), (403, 403, 403))

    def test_hosted_switch_lets_a_coach_use_the_demo_in_production_only_when_set(self):
        """HOSTED_DEMO_ENABLED=true allows the coach in production (and no one else); without it production stays refused."""
        hosted = {"HOSTED_DEMO_ENABLED": "true", "DJANGO_ENV": "production"}
        self.client.force_authenticate(self.coach)
        with patch.dict(os.environ, hosted):
            self.assertEqual(self.client.get(STATUS).status_code, 200)
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "production", "HOSTED_DEMO_ENABLED": "false"}):
            self.assertEqual(self.client.get(STATUS).status_code, 403)
        for user in (self.admin, self.driver):
            self.client.force_authenticate(user)
            with patch.dict(os.environ, hosted):
                self.assertEqual(self.client.get(STATUS).status_code, 403)

    def test_rule_3_anonymous_request_rejected(self):
        """Anonymous callers get 401 or 403."""
        with patch.dict(os.environ, DEV):
            for code in self.all_three():
                self.assertIn(code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_rule_3_admin_and_driver_rejected_with_403(self):
        """Admin and driver may not even read the status."""
        with patch.dict(os.environ, DEV):
            for user in (self.admin, self.driver):
                self.client.force_authenticate(user)
                self.assertEqual(self.all_three(), (403, 403, 403), user.role)

    def test_rule_3_coach_role_allowed(self):
        """A coach can read the status."""
        self.client.force_authenticate(self.coach)
        with patch.dict(os.environ, DEV):
            response = self.client.get(STATUS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["state"], "idle")
