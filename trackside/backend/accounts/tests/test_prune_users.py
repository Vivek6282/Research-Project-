"""
Trackside — prune_users command tests.

Checks the safety rules: dry run by default, admins protected, users with
data protected unless asked, --keep honoured, and deletions are audited.
"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLogEntry, User
from tracks.models import Track
from driving_sessions.models import Session


class PruneUsersCommandTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@t.test", name="Admin", role="admin", password="x-Pass-123")
        self.unused_driver = User.objects.create_user(email="unused@t.test", name="Unused Driver", role="driver", password="x-Pass-123")
        self.test_coach = User.objects.create_user(email="coach-test@t.test", name="Test Coach", role="coach", password="x-Pass-123")
        self.busy_driver = User.objects.create_user(email="busy@t.test", name="Busy Driver", role="driver", password="x-Pass-123")
        track = Track.objects.create(name="Any Track", kart_class="sprint")
        Session.objects.create(driver=self.busy_driver, track=track, mode="safety", started_at=timezone.now())

    def run_command(self, *args):
        output = StringIO()
        call_command("prune_users", *args, stdout=output)
        return output.getvalue()

    def test_dry_run_deletes_nothing(self):
        output = self.run_command()
        self.assertIn("Dry run", output)
        self.assertEqual(User.objects.count(), 4)

    def test_apply_removes_only_unused_non_admin_users(self):
        self.run_command("--apply", "--yes")
        remaining = set(User.objects.values_list("email", flat=True))
        self.assertEqual(remaining, {"admin@t.test", "busy@t.test"})

    def test_admin_is_never_deleted_even_when_matched(self):
        self.run_command("--email-contains", "admin", "--apply", "--yes")
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_user_with_sessions_needs_include_with_data(self):
        self.run_command("--name-contains", "busy", "--apply", "--yes")
        self.assertTrue(User.objects.filter(pk=self.busy_driver.pk).exists())

        self.run_command("--name-contains", "busy", "--include-with-data", "--apply", "--yes")
        self.assertFalse(User.objects.filter(pk=self.busy_driver.pk).exists())

    def test_keep_protects_a_user(self):
        self.run_command("--keep", "unused@t.test", "--apply", "--yes")
        self.assertTrue(User.objects.filter(pk=self.unused_driver.pk).exists())
        self.assertFalse(User.objects.filter(pk=self.test_coach.pk).exists())

    def test_name_filter_limits_who_matches(self):
        self.run_command("--name-contains", "test", "--apply", "--yes")
        self.assertTrue(User.objects.filter(pk=self.unused_driver.pk).exists())
        self.assertFalse(User.objects.filter(pk=self.test_coach.pk).exists())

    def test_deletions_are_audited(self):
        self.run_command("--role", "coach", "--apply", "--yes")
        entry = AuditLogEntry.objects.get(action=AuditLogEntry.Action.DELETE_USER)
        self.assertEqual(entry.target_user_name, "Test Coach")

    def test_bad_date_is_rejected(self):
        with self.assertRaises(CommandError):
            self.run_command("--created-before", "31/01/2026")
