"""
Trackside — Demo Control log parsing, status fields and the child process environment.
"""

import io
from unittest.mock import MagicMock

from rest_framework.test import APITestCase

from demo_control import simulator
from demo_control.child_env import build_child_env
from demo_control.simulator import get_simulator_status, parse_friendly_error, reset_state_for_testing


class DemoControlStatusAndErrorParsingTests(APITestCase):
    """Friendly error text, bridge detection, lap tracking and status states."""

    def setUp(self):
        """Start from a clean simulator state."""
        super().setUp()
        reset_state_for_testing()
        self.addCleanup(reset_state_for_testing)

    def test_error_parsing_module_not_found(self):
        """ModuleNotFoundError friendly text."""
        lines = ["Traceback (most recent call last):", "ModuleNotFoundError: No module named 'serial'"]
        self.assertEqual(parse_friendly_error(exit_code=1, lines=lines),
                         "Missing Python package: serial. Run: pip install -r trackside/demo/requirements.txt")

    def test_error_parsing_address_in_use(self):
        """Port in use error friendly text."""
        lines = ["[!] WebSocket server error: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8765): only one usage of each socket address is permitted"]
        self.assertEqual(parse_friendly_error(exit_code=1, lines=lines),
                         "Another simulator is already running (port 8765 is in use). Close it and try again.")

    def test_error_parsing_com_port_busy(self):
        """PermissionError / Access is denied friendly text."""
        lines = ["Connecting to Bridge ESP32 on COM5...",
                 "[!] Warning: Bridge ESP32 not detected on COM5 (could not open port COM5: PermissionError(13, 'Access is denied.', None, 5))."]
        self.assertEqual(parse_friendly_error(exit_code=1, lines=lines), "The COM port is busy. Close the Arduino Serial Monitor.")

    def test_error_parsing_generic_non_zero_exit_and_clean_exit(self):
        """A non-zero exit gives the generic text; a clean exit gives None."""
        self.assertEqual(parse_friendly_error(exit_code=2, lines=["Some unexpected failure"]),
                         "The simulator stopped with an error (exit code 2).")
        self.assertIsNone(parse_friendly_error(exit_code=0, lines=["Simulation session finished."]))

    def test_bridge_connected_and_disconnected_extraction(self):
        """Bridge state and port come from the simulator's own lines."""
        simulator._output_lines.extend(["Connecting to Bridge ESP32 on COM4...", "  [OK] Connected to Bridge ESP32 on COM4."])
        data = get_simulator_status()
        self.assertTrue(data["bridge_connected"])
        self.assertEqual(data["port_hint"], "COM4")
        simulator._output_lines.clear()
        simulator._output_lines.extend(["  [!] Warning: Bridge ESP32 not detected on COM7 (port not found)."])
        data = get_simulator_status()
        self.assertFalse(data["bridge_connected"])
        self.assertEqual(data["port_hint"], "COM7")

    def test_reader_tracks_the_current_lap(self):
        """The output reader notes the latest '===== LAP n' line."""
        proc = MagicMock()
        proc.stdout = io.BytesIO(b"hello\n===== LAP 1 / 3 =====\n  -> Turn 1 | peak 1.0g\n===== LAP 2 / 3 =====\n")
        simulator._reader_loop(proc)
        self.assertEqual(simulator._current_lap, 2)

    def test_idle_status_has_no_run(self):
        """With no run the state is idle and run is None."""
        data = get_simulator_status()
        self.assertEqual((data["state"], data["run"], data["running"]), ("idle", None, False))

    def test_state_words(self):
        """running, stopped, finished and failed are told apart."""
        self.assertEqual(simulator.run_state(True, None, False, True), "running")
        self.assertEqual(simulator.run_state(False, -15, True, True), "stopped")
        self.assertEqual(simulator.run_state(False, 0, False, True), "finished")
        self.assertEqual(simulator.run_state(False, 2, False, True), "failed")
        self.assertEqual(simulator.run_state(False, None, False, False), "idle")


class ChildEnvironmentTests(APITestCase):
    """Only an allow-list of the server's environment reaches the simulator."""

    def test_server_secrets_are_not_passed_on(self):
        """SECRET_KEY, database and admin settings stay in the server."""
        import os
        from unittest.mock import patch
        fake = {"PATH": "/bin", "SECRET_KEY": "s3cr3t", "DATABASE_URL": "sqlite:///x", "ADMIN_PASSWORD": "pw", "HOME": "/home/x"}
        with patch.dict(os.environ, fake, clear=True):
            env = build_child_env({"SESSION_ID": "s"})
        self.assertEqual(set(env), {"PATH", "HOME", "PYTHONUNBUFFERED", "PYTHONIOENCODING", "SESSION_ID"})

    def test_run_values_are_added_and_unknown_names_are_refused(self):
        """The four run variables are accepted; anything else raises."""
        env = build_child_env({"SESSION_ID": "a", "DEVICE_TOKEN": "b", "BACKEND_URL": "c", "DEMO_ZONES": "{}"})
        self.assertEqual((env["SESSION_ID"], env["DEVICE_TOKEN"]), ("a", "b"))
        with self.assertRaises(ValueError):
            build_child_env({"SECRET_KEY": "x"})
