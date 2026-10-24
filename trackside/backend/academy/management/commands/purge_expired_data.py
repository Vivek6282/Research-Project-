"""
Trackside — Delete data older than the academy's retention period (Phase 2.0).

    python manage.py purge_expired_data           # shows what would be deleted, deletes nothing
    python manage.py purge_expired_data --apply   # deletes it

Covers telemetry readings, device events and biometric readings. Sessions,
alerts, notes and the audit log are kept. Run it daily from cron or a Render
cron job (see backend/README.md).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academy.models import AcademySettings
from devices.event_models import DeviceEvent
from driving_sessions.models import BiometricReading, Telemetry

DAYS_PER_MONTH = 30


def retention_cutoff(now=None):
    """The moment before which data is expired: now minus the retention period (a month counts as 30 days)."""
    months = AcademySettings.current().retention_months
    return (now or timezone.now()) - timedelta(days=months * DAYS_PER_MONTH)


def expired_querysets(cutoff):
    """{label: queryset} of everything older than the cutoff, each judged by its own time field."""
    return {
        "telemetry readings": Telemetry.objects.filter(recorded_at__lt=cutoff),
        "device events": DeviceEvent.objects.filter(received_at__lt=cutoff),
        "biometric readings": BiometricReading.objects.filter(recorded_at__lt=cutoff),
    }


class Command(BaseCommand):
    """Show or delete expired telemetry, device events and biometric readings."""

    help = "Delete data older than the academy retention period (dry run unless --apply is given)."

    def add_arguments(self, parser):
        """--apply really deletes; without it the command only reports."""
        parser.add_argument("--apply", action="store_true", help="Delete the expired data (default: only show counts)")

    def handle(self, *args, **options):
        """Count, and with --apply delete, the expired rows in one transaction."""
        cutoff = retention_cutoff()
        querysets = expired_querysets(cutoff)
        verb = "Deleted" if options["apply"] else "Would delete"
        with transaction.atomic():
            for label, queryset in querysets.items():
                count = queryset.count()
                if options["apply"] and count:
                    queryset.delete()
                self.stdout.write(f"{verb} {count} {label} older than {cutoff:%Y-%m-%d %H:%M} UTC")
        if not options["apply"]:
            self.stdout.write("Nothing was deleted. Add --apply to delete.")
