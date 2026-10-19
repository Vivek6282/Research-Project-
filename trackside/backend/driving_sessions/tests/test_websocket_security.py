"""
Trackside — Security Tests for WebSocket Telemetry Streaming (S2).

Verifies WebSocket authentication, session ownership, origin validation,
message size limiting, and malformed JSON resilience.
Compatible with both Django's test runner and pytest.
"""

import json
from asgiref.sync import async_to_sync
from django.test import TransactionTestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from channels.testing import WebsocketCommunicator

from config.asgi import application
from tracks.models import Track
from driving_sessions.models import Session

User = get_user_model()


class WebSocketSecurityTestCase(TransactionTestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="ws_admin@test.local", name="Admin", role="admin", password="password123"
        )
        self.coach = User.objects.create_user(
            email="ws_coach@test.local", name="Coach", role="coach", password="password123"
        )
        self.driver_a = User.objects.create_user(
            email="ws_driver_a@test.local", name="Driver A", role="driver", password="password123"
        )
        self.driver_b = User.objects.create_user(
            email="ws_driver_b@test.local", name="Driver B", role="driver", password="password123"
        )
        self.track = Track.objects.create(name="WS Track", created_by=self.admin)
        self.session_a = Session.objects.create(
            driver=self.driver_a, track=self.track, started_at=timezone.now()
        )

    def _get_cookie_header(self, user):
        client = Client()
        client.force_login(user)
        session_id = client.cookies["sessionid"].value
        return f"sessionid={session_id}".encode("utf-8")

    def test_websocket_anonymous_rejected(self):
        """Anonymous connection is rejected with close code 4401."""
        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session_a.id}/telemetry/",
                headers=[(b"host", b"localhost"), (b"origin", b"http://localhost")],
            )

            connected, close_code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4401)
            await communicator.disconnect()

        async_to_sync(_test)()

    def test_websocket_driver_b_rejected_on_driver_a_session(self):
        """Driver B cannot access Driver A's session (close code 4403)."""
        cookie = self._get_cookie_header(self.driver_b)

        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session_a.id}/telemetry/",
                headers=[
                    (b"host", b"localhost"),
                    (b"origin", b"http://localhost"),
                    (b"cookie", cookie),
                ],
            )

            connected, close_code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4403)
            await communicator.disconnect()

        async_to_sync(_test)()

    def test_websocket_coach_accepted(self):
        """Coach is authorized to access any driver's session."""
        cookie = self._get_cookie_header(self.coach)

        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session_a.id}/telemetry/",
                headers=[
                    (b"host", b"localhost"),
                    (b"origin", b"http://localhost"),
                    (b"cookie", cookie),
                ],
            )

            connected, subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.disconnect()

        async_to_sync(_test)()

    def test_websocket_bad_origin_rejected(self):
        """Websocket connection from untrusted origin is rejected."""
        cookie = self._get_cookie_header(self.coach)

        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session_a.id}/telemetry/",
                headers=[
                    (b"host", b"localhost"),
                    (b"origin", b"http://evil-attacker.com"),
                    (b"cookie", cookie),
                ],
            )

            connected, close_code = await communicator.connect()
            self.assertFalse(connected)
            await communicator.disconnect()

        async_to_sync(_test)()

    def test_websocket_malformed_json_and_oversized_message_handled(self):
        """Malformed JSON and messages over 1 KB do not crash the consumer; ping works."""
        cookie = self._get_cookie_header(self.coach)

        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session_a.id}/telemetry/",
                headers=[
                    (b"host", b"localhost"),
                    (b"origin", b"http://localhost"),
                    (b"cookie", cookie),
                ],
            )

            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Send malformed JSON (must not crash consumer)
            await communicator.send_to(text_data="{malformed json !!!")

            # Send oversized message (> 1 KB) (must be ignored)
            oversized = "a" * 2000
            await communicator.send_to(text_data=json.dumps({"msg": oversized}))

            # Verify consumer is still healthy and responds to ping
            await communicator.send_to(text_data=json.dumps({"type": "ping"}))
            response = await communicator.receive_json_from()
            self.assertEqual(response, {"type": "pong"})

            await communicator.disconnect()

        async_to_sync(_test)()
