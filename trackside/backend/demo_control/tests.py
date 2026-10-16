"""
Trackside — Demo Control Unit and Integration Tests.

Verifies:
Rule 1: 404 when DEMO_TOOLS_ENABLED is not 'true'.
Rule 2: 403 when DJANGO_ENV is 'production'.
Rule 3: 403 for admin, driver and device; 401/403 for anonymous; 200 for coach.
Rule 4: Fixed command structure, laps must be integer 1..20 (400 on invalid), no dry-run.
Rule 5: 409 when already running, stop is idempotent.
Rule 6: AuditLogEntry created on start and stop.
Helper tests: Status format, friendly error parsing, bridge and port parsing.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import AuditLogEntry
from demo_control import simulator
from demo_control.simulator import (
    get_simulator_status,
    parse_friendly_error,
    reset_state_for_testing,
)

User = get_user_model()


class DemoControlSecurityTests(TestCase):
    """Tests enforcing the 6 mandatory security rules."""

    def setUp(self):
        reset_state_for_testing()
        self.client = APIClient()

        # Create test users with distinct roles
        self.coach = User.objects.create_user(
            email="coach@trackside.local",
            name="Test Coach",
            role="coach",
            password="Password123!",
        )
        self.admin = User.objects.create_user(
            email="admin@trackside.local",
            name="Test Admin",
            role="admin",
            password="Password123!",
        )
        self.driver = User.objects.create_user(
            email="driver@trackside.local",
            name="Test Driver",
            role="driver",
            password="Password123!",
        )

        self.start_url = "/api/demo/simulator/start/"
        self.stop_url = "/api/demo/simulator/stop/"
        self.status_url = "/api/demo/simulator/status/"

    def tearReset(self):
        reset_state_for_testing()

    # -----------------------------------------------------------------------
    # Rule 1: OFF unless env DEMO_TOOLS_ENABLED=true (default false). When off, returns 404.
    # -----------------------------------------------------------------------
    def test_rule_1_off_when_demo_tools_disabled_returns_404(self):
        """When DEMO_TOOLS_ENABLED is false or unset, all endpoints return 404."""
        self.client.force_authenticate(user=self.coach)

        for env_val in ["false", "0", "", None]:
            env_patch = {} if env_val is None else {"DEMO_TOOLS_ENABLED": env_val}
            with patch.dict(os.environ, env_patch, clear=(env_val is None)):
                if env_val is None and "DEMO_TOOLS_ENABLED" in os.environ:
                    del os.environ["DEMO_TOOLS_ENABLED"]

                res_start = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
                self.assertEqual(res_start.status_code, status.HTTP_404_NOT_FOUND)

                res_stop = self.client.post(self.stop_url, format="json")
                self.assertEqual(res_stop.status_code, status.HTTP_404_NOT_FOUND)

                res_status = self.client.get(self.status_url)
                self.assertEqual(res_status.status_code, status.HTTP_404_NOT_FOUND)

    # -----------------------------------------------------------------------
    # Rule 2: Refuse (403) when DJANGO_ENV=production.
    # -----------------------------------------------------------------------
    def test_rule_2_refuse_when_production_returns_403(self):
        """Refuse with 403 when DJANGO_ENV is production."""
        self.client.force_authenticate(user=self.coach)

        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "production"}):
            res_start = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
            self.assertEqual(res_start.status_code, status.HTTP_403_FORBIDDEN)

            res_stop = self.client.post(self.stop_url, format="json")
            self.assertEqual(res_stop.status_code, status.HTTP_403_FORBIDDEN)

            res_status = self.client.get(self.status_url)
            self.assertEqual(res_status.status_code, status.HTTP_403_FORBIDDEN)

    # -----------------------------------------------------------------------
    # Rule 3: Only role "coach" may call it (403 for admin, driver, device; 401/403 for anonymous).
    # -----------------------------------------------------------------------
    def test_rule_3_anonymous_request_rejected(self):
        """Anonymous requests must be rejected (401 or 403)."""
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            res_start = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
            self.assertIn(res_start.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

            res_status = self.client.get(self.status_url)
            self.assertIn(res_status.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_rule_3_admin_and_driver_rejected_with_403(self):
        """Admin and driver roles must be rejected with 403."""
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            # Admin role
            self.client.force_authenticate(user=self.admin)
            res_admin = self.client.get(self.status_url)
            self.assertEqual(res_admin.status_code, status.HTTP_403_FORBIDDEN)

            res_admin_start = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
            self.assertEqual(res_admin_start.status_code, status.HTTP_403_FORBIDDEN)

            # Driver role
            self.client.force_authenticate(user=self.driver)
            res_driver = self.client.get(self.status_url)
            self.assertEqual(res_driver.status_code, status.HTTP_403_FORBIDDEN)

            res_driver_start = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
            self.assertEqual(res_driver_start.status_code, status.HTTP_403_FORBIDDEN)

    def test_rule_3_coach_role_allowed(self):
        """Coach role is permitted to access all endpoints."""
        self.client.force_authenticate(user=self.coach)
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            res_status = self.client.get(self.status_url)
            self.assertEqual(res_status.status_code, status.HTTP_200_OK)

    # -----------------------------------------------------------------------
    # Rule 4: Fixed command and laps validation (1..20, otherwise 400).
    # -----------------------------------------------------------------------
    def test_rule_4_laps_validation(self):
        """Laps must be an integer 1..20; invalid inputs must return 400."""
        self.client.force_authenticate(user=self.coach)
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            # Invalid modes
            res = self.client.post(self.start_url, {"mode": "invalid"}, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

            # Invalid laps values
            invalid_laps = [0, 21, -5, "3", 3.5, None, True, False, "many"]
            for bad_lap in invalid_laps:
                res = self.client.post(self.start_url, {"mode": "laps", "laps": bad_lap}, format="json")
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, f"Failed on laps={bad_lap}")

    @patch("subprocess.Popen")
    def test_rule_4_command_is_fixed_and_no_dry_run(self, mock_popen):
        """Verify the exact command structure: python -u simulator.py --laps 5 or --continuous."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None
        mock_proc.stdout.readline.return_value = b""
        mock_popen.return_value = mock_proc

        self.client.force_authenticate(user=self.coach)
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            # 1. Mode laps
            res = self.client.post(self.start_url, {"mode": "laps", "laps": 5}, format="json")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

            mock_popen.assert_called_once()
            cmd_called = mock_popen.call_args[0][0]
            cwd_called = mock_popen.call_args[1]["cwd"]
            env_called = mock_popen.call_args[1]["env"]

            self.assertIn("-u", cmd_called)
            self.assertTrue(cmd_called[2].endswith("virtual_lap_simulator.py"))
            self.assertEqual(cmd_called[3:], ["--laps", "5"])
            self.assertNotIn("--dry-run", cmd_called)
            self.assertTrue(cwd_called.endswith("demo"))
            self.assertEqual(env_called["PYTHONUNBUFFERED"], "1")
            self.assertEqual(env_called["PYTHONIOENCODING"], "utf-8")

        reset_state_for_testing()
        mock_popen.reset_mock()

        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            # 2. Mode continuous
            res = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

            cmd_called = mock_popen.call_args[0][0]
            self.assertEqual(cmd_called[3:], ["--continuous"])
            self.assertNotIn("--dry-run", cmd_called)

    # -----------------------------------------------------------------------
    # Rule 5: One at a time: 409 if already running. Stop is idempotent.
    # -----------------------------------------------------------------------
    @patch("subprocess.Popen")
    def test_rule_5_one_at_a_time_409_and_idempotent_stop(self, mock_popen):
        """Starting while already running returns 409. Stop is idempotent."""
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = None
        mock_proc.stdout.readline.return_value = b""
        mock_popen.return_value = mock_proc

        self.client.force_authenticate(user=self.coach)
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            # First start succeeds
            res1 = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
            self.assertEqual(res1.status_code, status.HTTP_200_OK)

            # Second start returns 409
            res2 = self.client.post(self.start_url, {"mode": "continuous"}, format="json")
            self.assertEqual(res2.status_code, status.HTTP_409_CONFLICT)

            # First stop succeeds
            res_stop1 = self.client.post(self.stop_url, format="json")
            self.assertEqual(res_stop1.status_code, status.HTTP_200_OK)

            # Second stop also succeeds (idempotent)
            mock_proc.poll.return_value = 0
            res_stop2 = self.client.post(self.stop_url, format="json")
            self.assertEqual(res_stop2.status_code, status.HTTP_200_OK)

    # -----------------------------------------------------------------------
    # Rule 6: Write an AuditLogEntry on start and on stop.
    # -----------------------------------------------------------------------
    @patch("subprocess.Popen")
    def test_rule_6_audit_log_entry_on_start_and_stop(self, mock_popen):
        """AuditLogEntry records are written on start and stop with actor=coach."""
        mock_proc = MagicMock()
        mock_proc.pid = 5432
        mock_proc.poll.return_value = None
        mock_proc.stdout.readline.return_value = b""
        mock_popen.return_value = mock_proc

        self.client.force_authenticate(user=self.coach)
        with patch.dict(os.environ, {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}):
            AuditLogEntry.objects.all().delete()

            # Start
            self.client.post(self.start_url, {"mode": "laps", "laps": 3}, format="json")
            start_entry = AuditLogEntry.objects.filter(action=AuditLogEntry.Action.SIMULATOR_START).first()
            self.assertIsNotNone(start_entry)
            self.assertEqual(start_entry.actor, self.coach)
            self.assertIn("mode 'laps'", start_entry.details)

            # Stop
            self.client.post(self.stop_url, format="json")
            stop_entry = AuditLogEntry.objects.filter(action=AuditLogEntry.Action.SIMULATOR_STOP).first()
            self.assertIsNotNone(stop_entry)
            self.assertEqual(stop_entry.actor, self.coach)


class DemoControlStatusAndErrorParsingTests(TestCase):
    """Tests for status JSON formatting and friendly error text parsing."""

    def setUp(self):
        reset_state_for_testing()

    def tearDown(self):
        reset_state_for_testing()

    def test_error_parsing_module_not_found(self):
        """ModuleNotFoundError friendly text."""
        lines = [
            "Traceback (most recent call last):",
            "ModuleNotFoundError: No module named 'serial'",
        ]
        err = parse_friendly_error(exit_code=1, lines=lines)
        self.assertEqual(err, "Missing Python package: serial. Run: pip install -r trackside/demo/requirements.txt")

    def test_error_parsing_address_in_use(self):
        """Port in use error friendly text."""
        lines = [
            "[!] WebSocket server error: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8765): only one usage of each socket address is permitted",
        ]
        err = parse_friendly_error(exit_code=1, lines=lines)
        self.assertEqual(err, "Another simulator is already running (port 8765 is in use). Close it and try again.")

    def test_error_parsing_com_port_busy(self):
        """PermissionError / Access is denied friendly text."""
        lines = [
            "Connecting to Bridge ESP32 on COM5...",
            "[!] Warning: Bridge ESP32 not detected on COM5 (could not open port COM5: PermissionError(13, 'Access is denied.', None, 5)).",
        ]
        err = parse_friendly_error(exit_code=1, lines=lines)
        self.assertEqual(err, "The COM port is busy. Close the Arduino Serial Monitor.")

    def test_error_parsing_generic_non_zero_exit(self):
        """Generic non-zero exit code friendly text."""
        lines = ["Some unexpected failure"]
        err = parse_friendly_error(exit_code=2, lines=lines)
        self.assertEqual(err, "The simulator stopped with an error (exit code 2).")

    def test_error_parsing_clean_exit(self):
        """Clean exit returns None."""
        lines = ["Simulation session finished."]
        err = parse_friendly_error(exit_code=0, lines=lines)
        self.assertIsNone(err)

    def test_bridge_connected_and_port_hint_extraction(self):
        """Extracts bridge_connected and port_hint from simulator output."""
        simulator._output_lines.extend([
            "Connecting to Bridge ESP32 on COM4...",
            "  [OK] Connected to Bridge ESP32 on COM4.",
        ])

        status_data = get_simulator_status()
        self.assertTrue(status_data["bridge_connected"])
        self.assertEqual(status_data["port_hint"], "COM4")

    def test_bridge_disconnected_extraction(self):
        """Detects disconnected bridge and port hint."""
        simulator._output_lines.extend([
            "Connecting to Bridge ESP32 on COM7...",
            "  [!] Warning: Bridge ESP32 not detected on COM7 (port not found).",
        ])

        status_data = get_simulator_status()
        self.assertFalse(status_data["bridge_connected"])
        self.assertEqual(status_data["port_hint"], "COM7")
