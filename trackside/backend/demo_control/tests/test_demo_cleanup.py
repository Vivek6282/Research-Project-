"""
Trackside — Demo run device rules, one-at-a-time, stop and clean-up (H4).
"""

from django.utils import timezone

from accounts.models import AuditLogEntry
from demo_control import simulator
from demo_control.demo_run import DEMO_DEVICE_NAME
from demo_control.tests.demo_run_base import STATUS, STOP, DemoRunBase
from devices.models import Device
from driving_sessions.models import Session


class TestDeviceRules(DemoRunBase):
    """The one-kart-unit-per-driver rule and moving the demo device."""

    def test_driver_with_another_kart_unit_is_refused_and_told_which(self):
        """409 naming the driver's own kart unit; nothing is changed."""
        own = Device.objects.create(device_type="kart_unit", assigned_to=self.ana)
        response = self.start()
        self.assertEqual(response.status_code, 409)
        self.assertIn("Ana Driver already has kart unit", response.data["error"])
        self.assertIn(str(own.id)[:8], response.data["error"])
        self.assertEqual(Session.objects.count(), 0)
        own.refresh_from_db()
        self.assertEqual(own.assigned_to, self.ana)

    def test_driver_with_a_glove_is_fine(self):
        """Only a different kart unit blocks; a glove does not."""
        Device.objects.create(device_type="glove", assigned_to=self.ana)
        self.assertEqual(self.start().status_code, 200)

    def test_the_demo_device_moves_between_drivers_with_an_audit_trail(self):
        """Run 1 for Ana, run 2 for Ben: the device ends with Ben and both moves are in the audit log."""
        self.start()
        self.proc.poll.return_value = 0
        self.assertEqual(self.start(driver_id=str(self.ben.id)).status_code, 200)
        self.assertEqual(self.demo_device().assigned_to, self.ben)
        actions = list(AuditLogEntry.objects.filter(action__in=[
            AuditLogEntry.Action.DEVICE_ASSIGNED, AuditLogEntry.Action.DEVICE_UNASSIGNED]).values_list("action", flat=True))
        self.assertIn(AuditLogEntry.Action.DEVICE_ASSIGNED, actions)
        self.assertGreaterEqual(len(actions), 3)


class TestOneAtATimeStopAndCleanup(DemoRunBase):
    """409 for a second run, idempotent stop, and clean-up after every kind of ending."""

    def test_second_start_is_refused_while_running(self):
        """409 with a clear message; nothing new is created."""
        self.assertEqual(self.start().status_code, 200)
        response = self.start(driver_id=str(self.ben.id))
        self.assertEqual(response.status_code, 409)
        self.assertIn("already running", response.data["error"])
        self.assertEqual(Session.objects.count(), 1)

    def test_stop_closes_the_session_unassigns_the_device_and_kills_the_token(self):
        """After stop: ended_at set, device unassigned, token empty, state 'stopped', audit entries written."""
        self.start()
        token = self.popen_mock.call_args[1]["env"]["DEVICE_TOKEN"]
        self.assertEqual(self.client.post(STOP).status_code, 200)
        self.proc.terminate.assert_called()
        self.proc.poll.return_value = -15
        session = Session.objects.get()
        self.assertEqual(self.client.get(STATUS).data["state"], "stopped")
        session.refresh_from_db()
        device = self.demo_device()
        self.assertIsNotNone(session.ended_at)
        self.assertIsNone(device.assigned_to)
        self.assertFalse(device.verify_api_key(token))
        self.assertEqual(device.api_key_hash, "")
        self.assertTrue(AuditLogEntry.objects.filter(action=AuditLogEntry.Action.SIMULATOR_STOP, actor=self.coach).exists())

    def test_stop_is_idempotent(self):
        """Stopping twice, or with nothing running, still answers 200."""
        self.assertEqual(self.client.post(STOP).status_code, 200)
        self.start()
        self.assertEqual(self.client.post(STOP).status_code, 200)
        self.proc.poll.return_value = -15
        self.assertEqual(self.client.post(STOP).status_code, 200)

    def test_natural_finish_is_cleaned_up_when_status_is_read(self):
        """Process exits 0: status says finished, the session is closed, the device released, the token dead."""
        self.start()
        self.proc.poll.return_value = 0
        data = self.client.get(STATUS).data
        self.assertEqual(data["state"], "finished")
        self.assertEqual(data["run"]["track_name"], "Run Track")
        self.assertNotIn("DEVICE_TOKEN", str(data))
        self.assertIsNotNone(Session.objects.get().ended_at)
        self.assertIsNone(self.demo_device().assigned_to)
        self.assertEqual(self.demo_device().api_key_hash, "")

    def test_a_crash_shows_failed(self):
        """A non-zero exit is 'failed' with the friendly error text."""
        self.start()
        self.proc.poll.return_value = 3
        data = self.client.get(STATUS).data
        self.assertEqual(data["state"], "failed")
        self.assertIn("exit code 3", data["error"])

    def test_status_while_running_shows_the_lap(self):
        """Running state, the run facts and the lap x of y numbers."""
        self.start(laps=5)
        simulator._current_lap = 2
        data = self.client.get(STATUS).data
        self.assertEqual((data["state"], data["current_lap"], data["laps"]), ("running", 2, 5))
        self.assertEqual(data["run"]["driver_name"], "Ana Driver")

    def test_leftovers_from_a_server_restart_are_cleaned_on_the_next_start(self):
        """An open demo session and an assigned demo device with no running process are closed and released."""
        device = Device.objects.create(name=DEMO_DEVICE_NAME, device_type="kart_unit", assigned_to=self.ben)
        device.set_api_key()
        device.save()
        old = Session.objects.create(driver=self.ben, track=self.track, started_at=timezone.now(), is_demo=True)
        self.assertEqual(self.start().status_code, 200)
        old.refresh_from_db()
        self.assertIsNotNone(old.ended_at)
        self.assertEqual(self.demo_device().assigned_to, self.ana)

    def test_a_real_session_is_never_touched_by_clean_up(self):
        """Open sessions that are not demo runs stay open."""
        real = Session.objects.create(driver=self.ben, track=self.track, started_at=timezone.now())
        self.start()
        self.client.post(STOP)
        real.refresh_from_db()
        self.assertIsNone(real.ended_at)

    def test_spawn_failure_rolls_back(self):
        """If the process cannot start, the session is closed and the device released."""
        self.popen_mock.side_effect = OSError("no python")
        response = self.start()
        self.assertEqual(response.status_code, 500)
        self.assertIsNotNone(Session.objects.get().ended_at)
        self.assertIsNone(self.demo_device().assigned_to)
