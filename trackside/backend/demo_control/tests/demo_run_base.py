"""
Trackside — Shared set-up for the demo run tests: users, a custom map, and a fake simulator process.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from demo_control.demo_run import DEMO_DEVICE_NAME
from demo_control.simulator import reset_state_for_testing
from devices.models import Device
from tracks.tests.track_factory import make_imported_track

User = get_user_model()
DEV = {"DEMO_TOOLS_ENABLED": "true", "DJANGO_ENV": "development"}
START, STOP, STATUS = "/api/demo/simulator/start/", "/api/demo/simulator/stop/", "/api/demo/simulator/status/"


def fake_process(pid=4242):
    """A stand-in for the simulator process that stays 'running' until poll is changed."""
    proc = MagicMock()
    proc.pid = pid
    proc.poll.return_value = None
    proc.stdout.readline.return_value = b""
    return proc


class DemoRunBase(APITestCase):
    """A coach, two drivers, a custom four-corner map and the built-in map."""

    def setUp(self):
        """Create users and maps, point profile files at a temp folder, and enable demo tools."""
        super().setUp()
        reset_state_for_testing()
        self.addCleanup(reset_state_for_testing)
        make = User.objects.create_user
        self.coach = make(email="run_coach@trackside.local", name="Coach", role="coach", password="Password123!")
        self.admin = make(email="run_admin@trackside.local", name="Admin", role="admin", password="Password123!")
        self.ana = make(email="run_ana@trackside.local", name="Ana Driver", role="driver", password="Password123!")
        self.ben = make(email="run_ben@trackside.local", name="Ben Driver", role="driver", password="Password123!")
        self.track = make_imported_track(self.coach, name="Run Track", limit=1.2)
        self.client.force_authenticate(self.coach)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.profile_dir = os.path.join(folder.name, "profiles")
        for patcher in (patch.dict(os.environ, DEV), patch("demo_control.demo_run.profile_directory", return_value=self.profile_dir)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.popen = patch("subprocess.Popen")
        self.popen_mock = self.popen.start()
        self.addCleanup(self.popen.stop)
        self.proc = fake_process()
        self.popen_mock.return_value = self.proc

    def start(self, **override):
        """POST a start request for the custom map and Ana, 2 laps, edge pace."""
        body = {"track_id": str(self.track.id), "driver_id": str(self.ana.id), "laps": 2, "pace": "edge"}
        body.update(override)
        return self.client.post(START, body, format="json")

    def demo_device(self):
        """The dedicated demo device."""
        return Device.objects.get(name=DEMO_DEVICE_NAME)
