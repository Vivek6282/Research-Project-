"""
Trackside — the simulator waits for a slow server instead of losing the end of the run.
"""

import os
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch

demo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if demo_dir not in sys.path:
    sys.path.insert(0, demo_dir)

import sim_backend_poster as poster
import sim_backpressure as pressure


class FakeWorker:
    """Stands in for the upload thread: alive, and it takes one reading off the queue every drain_s seconds."""

    def __init__(self, drain_s):
        self.drain_s = drain_s
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            time.sleep(self.drain_s)
            try:
                poster.TELEMETRY_QUEUE.get_nowait()
            except queue.Empty:
                pass

    def is_alive(self):
        return True


class BackpressureTests(unittest.TestCase):

    def setUp(self):
        while not poster.TELEMETRY_QUEUE.empty():
            poster.TELEMETRY_QUEUE.get_nowait()
        poster.SHUTDOWN_EVENT.clear()
        pressure.paused_total_s = 0.0

    def tearDown(self):
        while not poster.TELEMETRY_QUEUE.empty():
            poster.TELEMETRY_QUEUE.get_nowait()

    def fill(self, count):
        for n in range(count):
            poster.TELEMETRY_QUEUE.put_nowait({"n": n})

    def test_no_pause_when_nothing_is_being_posted(self):
        """Without an upload thread (no session or token) the call returns at once."""
        self.fill(50)
        with patch.object(poster, "BACKEND_WORKER_THREAD", None):
            started = time.monotonic()
            pressure.wait_for_backend_room()
        self.assertLess(time.monotonic() - started, 0.2)

    def test_no_pause_while_the_backlog_is_small(self):
        """A backlog within the limit does not slow the run."""
        self.fill(pressure.MAX_BACKLOG)
        with patch.object(poster, "BACKEND_WORKER_THREAD", FakeWorker(1.0)):
            started = time.monotonic()
            pressure.wait_for_backend_room()
        self.assertLess(time.monotonic() - started, 0.2)

    def test_pauses_until_the_server_has_caught_up(self):
        """A long backlog holds the clock until it is back within the limit, and no reading is dropped."""
        self.fill(pressure.MAX_BACKLOG + 6)
        worker = FakeWorker(0.05)
        worker.thread.start()
        try:
            with patch.object(poster, "BACKEND_WORKER_THREAD", worker):
                pressure.wait_for_backend_room()
            self.assertLessEqual(poster.TELEMETRY_QUEUE.qsize(), pressure.MAX_BACKLOG)
            self.assertGreater(pressure.paused_total_s, 0.1)
        finally:
            worker.stop.set()

    def test_a_stuck_server_cannot_hold_one_reading_for_long(self):
        """If nothing drains, one reading waits at most the per-reading limit, then the run goes on."""
        self.fill(pressure.MAX_BACKLOG + 5)
        with patch.object(poster, "BACKEND_WORKER_THREAD", FakeWorker(1000)), \
                patch.object(pressure, "MAX_PAUSE_PER_READING_S", 0.3):
            started = time.monotonic()
            pressure.wait_for_backend_room()
            took = time.monotonic() - started
        self.assertGreaterEqual(took, 0.28)
        self.assertLess(took, 1.0)

    def test_a_dead_server_is_given_up_on_after_the_run_budget(self):
        """Once the whole-run pause budget is used up, later readings are not delayed at all."""
        self.fill(pressure.MAX_BACKLOG + 5)
        pressure.paused_total_s = pressure.MAX_PAUSE_PER_RUN_S
        with patch.object(poster, "BACKEND_WORKER_THREAD", FakeWorker(1000)):
            started = time.monotonic()
            pressure.wait_for_backend_room()
        self.assertLess(time.monotonic() - started, 0.2)

    def test_no_pause_once_shutdown_has_begun(self):
        """While the run is closing, the drain is handled by the flush, not by pausing."""
        self.fill(pressure.MAX_BACKLOG + 5)
        poster.SHUTDOWN_EVENT.set()
        with patch.object(poster, "BACKEND_WORKER_THREAD", FakeWorker(1000)):
            started = time.monotonic()
            pressure.wait_for_backend_room()
        self.assertLess(time.monotonic() - started, 0.2)


class RunnersUseTheWait(unittest.TestCase):

    def test_both_runners_call_it_after_posting_each_reading(self):
        """The Demo Circuit loop and the custom-map loop both pause through the same function."""
        for name in ("virtual_lap_simulator.py", "sim_profile_run.py"):
            text = open(os.path.join(demo_dir, name), encoding="utf-8").read()
            self.assertIn("wait_for_backend_room()", text, name)

    def test_the_final_flush_waits_long_enough_to_drain(self):
        """The end-of-run flush is given 30 seconds, not 5, to empty the queue before the session closes."""
        text = open(os.path.join(demo_dir, "virtual_lap_simulator.py"), encoding="utf-8").read()
        self.assertIn("timeout_seconds=30.0", text)


if __name__ == "__main__":
    unittest.main()
