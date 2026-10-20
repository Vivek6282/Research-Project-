"""
Unit tests for WebSocket Origin validation (Prompt 6b H4).
Verifies exact origin matching, rejection of prefix and subdomain attacks,
null origin toggle via WS_ALLOW_NULL_ORIGIN, and allowance of clients without Origin headers.
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
    get_actual_port,
    is_origin_allowed,
    normalize_origin,
    start_websocket_server,
)


class WebSocketOriginTests(unittest.TestCase):
    """
    Tests for WebSocket origin security rules.
    """

    @classmethod
    def setUpClass(cls):
        """
        Starts the simulator WebSocket server on a free OS-assigned port.
        """
        cls.server_thread = start_websocket_server(host="127.0.0.1", port=0)
        cls.port = get_actual_port()
        assert cls.port is not None and cls.port > 0

    def test_normalize_origin(self):
        """
        Verifies case-insensitive normalization of origin schemes and host authorities.
        """
        self.assertEqual(normalize_origin("http://localhost:5173"), "http://localhost:5173")
        self.assertEqual(normalize_origin("HTTP://LOCALHOST:5173"), "http://localhost:5173")
        self.assertEqual(normalize_origin("http://127.0.0.1:5173"), "http://127.0.0.1:5173")
        self.assertEqual(normalize_origin("null"), "null")
        self.assertEqual(normalize_origin("NULL"), "null")
        self.assertEqual(normalize_origin(""), "")

    def test_is_origin_allowed_rule_decisions(self):
        """
        Tests exact origin authorization decisions and prefix attack rejections.
        """
        # Exact allowed origins
        self.assertTrue(is_origin_allowed("http://localhost:5173"))
        self.assertTrue(is_origin_allowed("HTTP://LOCALHOST:5173"))
        self.assertTrue(is_origin_allowed("http://127.0.0.1:5173"))

        # Prefix and subdomain tricks must be rejected
        self.assertFalse(is_origin_allowed("http://127.0.0.1:51730"))
        self.assertFalse(is_origin_allowed("http://localhost:5173.evil.com"))
        self.assertFalse(is_origin_allowed("http://attacker.com"))
        self.assertFalse(is_origin_allowed("file://"))

        # Client with no Origin header is allowed (local tools, CLI)
        self.assertTrue(is_origin_allowed(None))

    def test_null_origin_default_and_toggle(self):
        """
        Tests that null origin is accepted by default and rejected when WS_ALLOW_NULL_ORIGIN is false.
        """
        # Default environment: null accepted
        old_val = os.environ.get("WS_ALLOW_NULL_ORIGIN")
        try:
            os.environ["WS_ALLOW_NULL_ORIGIN"] = "true"
            self.assertTrue(is_origin_allowed("null"))

            os.environ["WS_ALLOW_NULL_ORIGIN"] = "false"
            self.assertFalse(is_origin_allowed("null"))
        finally:
            if old_val is not None:
                os.environ["WS_ALLOW_NULL_ORIGIN"] = old_val
            else:
                os.environ.pop("WS_ALLOW_NULL_ORIGIN", None)

    def test_live_socket_connection_origin_enforcement(self):
        """
        Tests that live WebSocket connections enforce exact origin and reject attacks with code 1008.
        """
        port = self.port

        async def run_checks():
            uri = f"ws://127.0.0.1:{port}"

            # 1. Exact allowed origin connects successfully
            async with websockets.connect(uri, origin="http://localhost:5173") as client:
                raw = await asyncio.wait_for(client.recv(), timeout=2.0)
                data = json.loads(raw)
                self.assertEqual(data.get("type"), "connection_ack")

            # 2. Client with no origin connects successfully
            async with websockets.connect(uri) as client:
                raw = await asyncio.wait_for(client.recv(), timeout=2.0)
                data = json.loads(raw)
                self.assertEqual(data.get("type"), "connection_ack")

            # 3. Port prefix trick http://127.0.0.1:51730 is rejected with 1008
            with self.assertRaises(websockets.exceptions.ConnectionClosed) as ctx1:
                async with websockets.connect(uri, origin="http://127.0.0.1:51730") as client:
                    await client.recv()
            self.assertEqual(ctx1.exception.rcvd.code, 1008)

            # 4. Domain prefix trick http://localhost:5173.evil.com is rejected with 1008
            with self.assertRaises(websockets.exceptions.ConnectionClosed) as ctx2:
                async with websockets.connect(uri, origin="http://localhost:5173.evil.com") as client:
                    await client.recv()
            self.assertEqual(ctx2.exception.rcvd.code, 1008)

        asyncio.run(run_checks())


if __name__ == "__main__":
    unittest.main()
