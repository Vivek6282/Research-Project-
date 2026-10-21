"""
Trackside — Tests for starting, watching and stopping a Coach demo run (H4, H5).

The simulator process is replaced by a fake, so these tests check what the server
prepares (session, device, token, profile, command line, environment) and cleans up.
"""

import json
import os

from accounts.models import AuditLogEntry
from demo_control.demo_run import DEMO_DEVICE_NAME
from demo_control.tests.demo_run_base import START, DemoRunBase
from devices.models import Device
from driving_sessions.models import Session
from tracks.demo_circuit_setup import ensure_demo_circuit
from tracks.models import Track

class TestStartCustomMap(DemoRunBase):
    """What the server prepares for a custom-map run."""

    def test_start_creates_a_demo_session_and_assigns_the_demo_device(self):
        """200, a demo Session for Ana on the map, the demo device assigned to Ana with a working token."""
        response = self.start()
        self.assertEqual(response.status_code, 200, response.data)
        session = Session.objects.get(pk=response.data["session_id"])
        self.assertEqual((session.driver, session.track, session.is_demo, session.kart_number), (self.ana, self.track, True, "Demo"))
        self.assertIsNone(session.ended_at)
        device = self.demo_device()
        self.assertEqual((device.device_type, device.assigned_to), ("kart_unit", self.ana))
        self.assertEqual(response.data["pace_applied"], True)

    def test_command_line_is_fixed_and_holds_no_secret(self):
        """argv is exactly python -u simulator --laps 2 --track-file <uuid>.json --pace edge, no shell, no token."""
        self.start()
        args, kwargs = self.popen_mock.call_args
        argv = args[0]
        self.assertFalse(kwargs["shell"])
        self.assertEqual(argv[1], "-u")
        self.assertTrue(argv[2].endswith("virtual_lap_simulator.py"))
        self.assertEqual(argv[3:], ["--laps", "2", "--track-file", os.path.join(self.profile_dir, f"{self.track.id}.json"), "--pace", "edge"])
        secret = kwargs["env"]["DEVICE_TOKEN"]
        self.assertFalse(any(secret in part or str(Session.objects.get().id) in part for part in argv))
        self.assertTrue(os.path.exists(argv[6]))

    def test_environment_carries_the_run_and_not_server_secrets(self):
        """SESSION_ID, DEVICE_TOKEN, BACKEND_URL and DEMO_ZONES are set; SECRET_KEY is not passed."""
        self.start()
        env = self.popen_mock.call_args[1]["env"]
        session = Session.objects.get()
        self.assertEqual(env["SESSION_ID"], str(session.id))
        self.assertTrue(env["BACKEND_URL"].startswith("http://testserver"))
        self.assertTrue(self.demo_device().verify_api_key(env["DEVICE_TOKEN"]))
        self.assertEqual(set(json.loads(env["DEMO_ZONES"])), {"Corner 1", "Corner 2", "Corner 3", "Corner 4"})
        self.assertNotIn("SECRET_KEY", env)
        self.assertNotIn("DATABASE_URL", env)

    def test_each_run_gets_a_fresh_token_and_the_old_one_stops_working(self):
        """The token from run 1 no longer verifies after run 2 starts."""
        self.start()
        first = self.popen_mock.call_args[1]["env"]["DEVICE_TOKEN"]
        self.proc.poll.return_value = 0
        self.assertEqual(self.start().status_code, 200)
        second = self.popen_mock.call_args[1]["env"]["DEVICE_TOKEN"]
        device = self.demo_device()
        self.assertNotEqual(first, second)
        self.assertFalse(device.verify_api_key(first))
        self.assertTrue(device.verify_api_key(second))

    def test_the_demo_device_is_created_once(self):
        """Two runs use the same single device."""
        self.start()
        self.proc.poll.return_value = 0
        self.start(driver_id=str(self.ben.id))
        self.assertEqual(Device.objects.filter(name=DEMO_DEVICE_NAME).count(), 1)

    def test_start_writes_an_audit_entry(self):
        """The start is logged with the map, driver, laps and pace."""
        self.start()
        entry = AuditLogEntry.objects.filter(action=AuditLogEntry.Action.SIMULATOR_START).get()
        self.assertEqual(entry.actor, self.coach)
        for word in ("Run Track", "Ana Driver", "2 laps", "edge"):
            self.assertIn(word, entry.details)


class TestStartBuiltin(DemoRunBase):
    """The Demo Circuit keeps its own simulation."""

    def test_builtin_run_has_no_track_file_or_pace_and_maps_the_three_corners(self):
        """argv is only --laps; DEMO_ZONES has Hairpin, Sweeper, Chicane; pace is reported as not applied."""
        demo = ensure_demo_circuit()
        response = self.client.post(START, {"track_id": str(demo.id), "driver_id": str(self.ana.id), "laps": 3, "pace": "over"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        args, kwargs = self.popen_mock.call_args
        self.assertEqual(args[0][3:], ["--laps", "3"])
        self.assertEqual(set(json.loads(kwargs["env"]["DEMO_ZONES"])), {"Hairpin", "Sweeper", "Chicane"})
        self.assertFalse(response.data["pace_applied"])
        self.assertFalse(os.path.exists(self.profile_dir))


class TestValidation(DemoRunBase):
    """Every bad request is a clear 400 and starts nothing."""

    def test_bad_inputs_are_refused_without_side_effects(self):
        """Bad ids, archived map, inactive or wrong-role driver, bad laps and pace."""
        self.ben.is_active = False
        self.ben.save()
        cases = {
            "no track": {"track_id": None},
            "junk track": {"track_id": "abc"},
            "unknown track": {"track_id": "00000000-0000-0000-0000-000000000000"},
            "no driver": {"driver_id": None},
            "unknown driver": {"driver_id": "00000000-0000-0000-0000-000000000000"},
            "coach as driver": {"driver_id": str(self.coach.id)},
            "inactive driver": {"driver_id": str(self.ben.id)},
            "laps 0": {"laps": 0}, "laps 21": {"laps": 21}, "laps text": {"laps": "3"},
            "laps float": {"laps": 2.5}, "laps true": {"laps": True}, "laps none": {"laps": None},
            "pace fast": {"pace": "fast"}, "pace number": {"pace": 1},
        }
        for name, override in cases.items():
            response = self.start(**override)
            self.assertEqual(response.status_code, 400, f"{name}: {response.data}")
            self.assertIn("error", response.data)
        self.assertEqual(Session.objects.count(), 0)
        self.assertEqual(Device.objects.filter(name=DEMO_DEVICE_NAME).count(), 0)
        self.popen_mock.assert_not_called()

    def test_laps_one_and_twenty_are_allowed(self):
        """The limits themselves are fine."""
        self.assertEqual(self.start(laps=1).status_code, 200)
        self.proc.poll.return_value = 0
        self.assertEqual(self.start(laps=20).status_code, 200)

    def test_archived_map_is_refused(self):
        """An archived map cannot be played."""
        Track.objects.filter(pk=self.track.pk).update(is_archived=True)
        response = self.start()
        self.assertEqual(response.status_code, 400)
        self.assertIn("archived", response.data["error"])

    def test_map_without_corners_or_outline_is_refused(self):
        """A map with no active corners, or no outline, cannot be played."""
        self.track.zones.update(is_active=False)
        self.assertIn("no corners", self.start().data["error"])
        bare = Track.objects.create(name="Bare Map")
        self.assertIn("no outline", self.start(track_id=str(bare.id)).data["error"])
        self.popen_mock.assert_not_called()

    def test_only_a_coach_may_start(self):
        """Admin gets 403 and nothing is created."""
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.start().status_code, 403)
        self.assertEqual(Session.objects.count(), 0)


