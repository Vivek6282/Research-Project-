"""
Trackside — Live readings with a zone must reach the coach's WebSocket (L0).

A reading that has a zone carries UUID values. They used to crash the consumer's
json.dumps, so the coach never saw anything. Now they arrive as plain strings.
"""

import json

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.test import Client, TransactionTestCase
from django.utils import timezone

from config.asgi import application
from driving_sessions.models import Alert, Session, Telemetry
from driving_sessions.signals import plain_json
from tracks.models import Track, Zone

User = get_user_model()


class LiveStreamJsonTests(TransactionTestCase):
    """The consumer and the signals both handle UUIDs."""

    def setUp(self):
        """Create a coach, a driver, a track with one zone and a session."""
        self.coach = User.objects.create_user(email="ls_coach@test.local", name="Coach", role="coach", password="password123")
        self.driver = User.objects.create_user(email="ls_driver@test.local", name="Driver", role="driver", password="password123")
        self.track = Track.objects.create(name="Live Track", created_by=self.coach)
        self.zone = Zone.objects.create(track=self.track, label="Hairpin", threshold_g=1.15)
        self.session = Session.objects.create(driver=self.driver, track=self.track, started_at=timezone.now())

    def connect(self):
        """A WebSocket communicator signed in as the coach."""
        client = Client()
        client.force_login(self.coach)
        cookie = f"sessionid={client.cookies['sessionid'].value}".encode()
        return WebsocketCommunicator(
            application, f"/ws/sessions/{self.session.id}/telemetry/",
            headers=[(b"host", b"localhost"), (b"origin", b"http://localhost"), (b"cookie", cookie)],
        )

    def test_reading_with_a_zone_reaches_the_coach_and_a_red_one_sends_an_alert(self):
        """The coach gets telemetry_reading then alert_triggered, with ids as strings."""
        communicator = self.connect()

        async def run():
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            from channels.db import database_sync_to_async
            reading = await database_sync_to_async(Telemetry.objects.create)(
                session=self.session, zone=self.zone, lateral_g=1.4, speed_kmh=50, gps_lat=0.0, gps_lng=0.0, recorded_at=timezone.now())
            alert = await database_sync_to_async(Alert.objects.create)(
                session=self.session, zone=self.zone, severity="red", g_value=1.4, threshold_applied=1.15, triggered_at=timezone.now())
            first = json.loads(await communicator.receive_from())
            second = json.loads(await communicator.receive_from())
            await communicator.disconnect()
            return reading, alert, first, second

        reading, alert, first, second = async_to_sync(run)()
        self.assertEqual(first["type"], "telemetry_reading")
        self.assertEqual(first["data"]["zone"], str(self.zone.id))
        self.assertEqual(first["data"]["id"], str(reading.id))
        self.assertEqual(second["type"], "alert_triggered")
        self.assertEqual(second["data"]["zone"], str(self.zone.id))

    def test_plain_json_turns_uuids_and_dates_into_strings(self):
        """The helper's output survives a plain json.dumps with no encoder."""
        data = plain_json({"id": self.zone.id, "when": timezone.now(), "n": 1})
        json.dumps(data)
        self.assertEqual(data["id"], str(self.zone.id))

    def test_the_consumer_source_uses_the_django_encoder(self):
        """All three event handlers pass cls=DjangoJSONEncoder (guards against a revert)."""
        import inspect
        from driving_sessions import consumers
        self.assertEqual(inspect.getsource(consumers).count("cls=DjangoJSONEncoder"), 3)
        self.assertIs(DjangoJSONEncoder, consumers.DjangoJSONEncoder)
