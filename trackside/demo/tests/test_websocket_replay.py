"""
Unit tests for WebSocket replay functionality (Prompt 6b H1).
Verifies late-joining visualizers receive replayed run_start with replay: true,
and that run_end clears the remembered run_start.
"""

import asyncio
import json
import os
import sys
import unittest

demo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if demo_dir not in sys.path:
    sys.path.insert(0, demo_dir)

import websockets
from sim_websocket_server import (
    broadcast_event,
    get_actual_port,
    reset_server_state,
    start_websocket_server,
)


class WebSocketReplayTests(unittest.TestCase):
    """
    Tests for replaying run_start to late-joining WebSocket clients.
    """

    @classmethod
    def setUpClass(cls):
        """
        Starts the simulator WebSocket server on a free OS-assigned port.
        """
        cls.server_thread = start_websocket_server(host="127.0.0.1", port=0)
        cls.port = get_actual_port()
        assert cls.port is not None and cls.port > 0

    def setUp(self):
        """
        Resets simulator server state before each test method.
        """
        reset_server_state()

    def test_late_joiner_gets_replayed_run_start_and_cleared_on_run_end(self):
        """
        Verifies that connecting after run_start yields connection_ack then replayed run_start,
        and connecting after run_end yields only connection_ack.
        """
        port = self.port

        async def run_scenario():
            # Broadcast run_start prior to client connection
            broadcast_event({
                "type": "run_start",
                "mode": "laps",
                "total_laps": 3,
            })
            await asyncio.sleep(0.05)

            # Late-joining client connects
            uri = f"ws://127.0.0.1:{port}"
            async with websockets.connect(uri) as client1:
                ack_raw = await asyncio.wait_for(client1.recv(), timeout=2.0)
                ack = json.loads(ack_raw)
                self.assertEqual(ack.get("type"), "connection_ack")

                replay_raw = await asyncio.wait_for(client1.recv(), timeout=2.0)
                replay = json.loads(replay_raw)
                self.assertEqual(replay.get("type"), "run_start")
                self.assertEqual(replay.get("mode"), "laps")
                self.assertEqual(replay.get("total_laps"), 3)
                self.assertTrue(replay.get("replay"))

            # Broadcast run_end
            broadcast_event({"type": "run_end"})
            await asyncio.sleep(0.05)

            # New client connects after run_end
            async with websockets.connect(uri) as client2:
                ack2_raw = await asyncio.wait_for(client2.recv(), timeout=2.0)
                ack2 = json.loads(ack2_raw)
                self.assertEqual(ack2.get("type"), "connection_ack")

                # Verify no second message arrives
                has_extra = False
                try:
                    await asyncio.wait_for(client2.recv(), timeout=0.3)
                    has_extra = True
                except asyncio.TimeoutError:
                    has_extra = False
                self.assertFalse(has_extra)

        asyncio.run(run_scenario())


if __name__ == "__main__":
    unittest.main()
