"""
Trackside — Tests for manage.py purge_expired_data (Phase 2.0, task 3).
"""

import uuid
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from academy.models import AcademySettings
from devices.event_models import DeviceEvent
from driving_sessions.models import Alert, BiometricReading, Session, Telemetry
from tracks.models import Track, Zone

User = get_user_model()


class TestPurgeExpiredData(TestCase):
    """One old (400 days) and one recent (10 days) row of each kind, plus a session and an alert to keep."""

    def setUp(self):
        """Create the fixture rows; received_at is set after saving because the model stamps it on create."""
        driver = User.objects.create_user(email="purge@t.local", name="Purge", password="Passw0rd!12345", role="driver")
        track = Track.objects.create(name="Purge Track")
        zone = Zone.objects.create(track=track, label="T1", threshold_g=1.2)
        self.session = Session.objects.create(driver=driver, track=track, started_at=timezone.now() - timedelta(days=400))
        Alert.objects.create(session=self.session, zone=zone, severity=Alert.Severity.RED, g_value=1.3,
                             threshold_applied=1.2, triggered_at=timezone.now() - timedelta(days=400))
        for days in (400, 10):
            moment = timezone.now() - timedelta(days=days)
            Telemetry.objects.create(session=self.session, lateral_g=0.5, speed_kmh=40, gps_lat=0, gps_lng=0, recorded_at=moment)
            BiometricReading.objects.create(session=self.session, recorded_at=moment, heart_rate=90, spo2=98, breathing_rate=15)
            event = DeviceEvent.objects.create(event_id=uuid.uuid4(), event_type="heartbeat", occurred_at=moment, sequence=1)
            DeviceEvent.objects.filter(pk=event.pk).update(received_at=moment)

    def run_purge(self, *args):
        """Run the command and return what it printed."""
        output = StringIO()
        call_command("purge_expired_data", *args, stdout=output)
        return output.getvalue()

    def counts(self):
        """(telemetry, biometrics, events) row counts."""
        return Telemetry.objects.count(), BiometricReading.objects.count(), DeviceEvent.objects.count()

    def test_dry_run_reports_and_deletes_nothing(self):
        """Default run: says 1 of each would go, keeps all 2 of each."""
        printed = self.run_purge()
        self.assertIn("Would delete 1 telemetry readings", printed)
        self.assertIn("Nothing was deleted", printed)
        self.assertEqual(self.counts(), (2, 2, 2))

    def test_apply_deletes_only_expired_rows_and_keeps_sessions_and_alerts(self):
        """--apply with 12 months: the 400-day rows go, the 10-day rows, the session and the alert stay."""
        printed = self.run_purge("--apply")
        self.assertIn("Deleted 1 device events", printed)
        self.assertEqual(self.counts(), (1, 1, 1))
        self.assertTrue(Session.objects.filter(pk=self.session.pk).exists())
        self.assertEqual(Alert.objects.count(), 1)

    def test_shorter_retention_removes_more(self):
        """A 60-day reading survives 12 months of retention but not 1 month."""
        Telemetry.objects.create(session=self.session, lateral_g=0.5, speed_kmh=40, gps_lat=0, gps_lng=0,
                                 recorded_at=timezone.now() - timedelta(days=60))
        self.assertIn("Would delete 1 telemetry readings", self.run_purge())
        settings_row = AcademySettings.current()
        settings_row.retention_months = 1
        settings_row.save()
        self.assertIn("Would delete 2 telemetry readings", self.run_purge())
        self.run_purge("--apply")
        self.assertEqual(Telemetry.objects.count(), 1)
