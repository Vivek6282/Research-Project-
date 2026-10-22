"""
Trackside — prune_users management command.

Cleans out accounts nobody needs (test users, leftovers from demos, people
who never drove). The API deliberately has no delete button, so this is the
one controlled place where users can be removed.

Safety rules, in plain words:
- It only LISTS what it would delete unless you pass --apply (a dry run).
- Admin accounts are never touched.
- By default it only removes users with nothing attached: no sessions, no
  coach notes and no assigned devices. Deleting a driver also deletes all of
  their sessions, telemetry and alerts, so that needs --include-with-data.
- Every deletion is written to the audit log.

Examples:
    python manage.py prune_users                       # dry run, unused users
    python manage.py prune_users --name-contains test  # dry run, names with "test"
    python manage.py prune_users --keep a@x.com --apply
"""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLogEntry

User = get_user_model()


class Command(BaseCommand):
    help = "List (dry run) or delete unneeded Coach/Driver accounts. Admins are never touched."

    def add_arguments(self, parser):
        parser.add_argument("--role", choices=["coach", "driver"], help="Only this kind of user.")
        parser.add_argument("--name-contains", action="append", default=[],
                            help="Match names containing this text (repeatable, case-insensitive).")
        parser.add_argument("--email-contains", action="append", default=[],
                            help="Match emails containing this text (repeatable, case-insensitive).")
        parser.add_argument("--inactive-only", action="store_true",
                            help="Only users that are already deactivated.")
        parser.add_argument("--created-before", help="Only users created before this date (YYYY-MM-DD).")
        parser.add_argument("--keep", action="append", default=[],
                            help="Email or username to protect from deletion (repeatable).")
        parser.add_argument("--include-with-data", action="store_true",
                            help="Also delete users that have sessions/notes/devices (their sessions go too).")
        parser.add_argument("--apply", action="store_true", help="Really delete. Without this it is a dry run.")
        parser.add_argument("--yes", action="store_true", help="Skip the confirmation question when applying.")

    def handle(self, *args, **options):
        candidates = self.find_candidates(options)
        self.print_report(candidates)

        if not candidates:
            self.stdout.write("Nothing to delete.")
            return
        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry run only. Nothing was deleted. Add --apply to delete these users."))
            return
        if not options["yes"] and input(f"Type DELETE to remove {len(candidates)} users: ") != "DELETE":
            raise CommandError("Cancelled. Nothing was deleted.")

        self.delete_users(candidates)
        self.stdout.write(self.style.SUCCESS(f"Deleted {len(candidates)} users."))

    # ---------- choosing who to delete ----------

    def find_candidates(self, options):
        """Apply every filter and return the users that would be deleted."""
        users = User.objects.exclude(role=User.Role.ADMIN).exclude(is_superuser=True)

        if options["role"]:
            users = users.filter(role=options["role"])
        if options["inactive_only"]:
            users = users.filter(is_active=False)
        if options["created_before"]:
            users = users.filter(created_at__lt=self.parse_date(options["created_before"]))

        users = self.filter_by_text(users, options)

        keep_values = options["keep"]
        if keep_values:
            users = users.exclude(email__in=keep_values).exclude(username__in=keep_values)

        users = users.distinct()
        if options["include_with_data"]:
            return list(users)
        return [user for user in users if not self.describe_data(user)]

    @staticmethod
    def filter_by_text(users, options):
        """Keep users whose name or email contains any of the given pieces of text."""
        from django.db.models import Q

        text_filter = Q()
        for text in options["name_contains"]:
            text_filter |= Q(name__icontains=text)
        for text in options["email_contains"]:
            text_filter |= Q(email__icontains=text)
        return users.filter(text_filter) if text_filter else users

    @staticmethod
    def parse_date(text):
        """Turn YYYY-MM-DD into a timezone-aware datetime, or explain the mistake."""
        try:
            return timezone.make_aware(datetime.strptime(text, "%Y-%m-%d"))
        except ValueError:
            raise CommandError("--created-before must look like 2026-01-31.")

    @staticmethod
    def describe_data(user):
        """Say what is attached to a user ('3 sessions, 1 device'); empty text means nothing."""
        parts = []
        for label, count in (
            ("sessions", user.sessions.count()),
            ("notes", user.session_notes.count()),
            ("devices", user.devices.count()),
        ):
            if count:
                parts.append(f"{count} {label}")
        return ", ".join(parts)

    # ---------- reporting and deleting ----------

    def print_report(self, candidates):
        """Show the people that matched, with what would be lost with each."""
        self.stdout.write(f"{len(candidates)} user(s) matched:")
        for user in candidates:
            attached = self.describe_data(user) or "no data"
            self.stdout.write(f"  {user.role:<7} {user.name} <{user.email or user.username}> active={user.is_active} ({attached})")

    @transaction.atomic
    def delete_users(self, candidates):
        """Delete all chosen users together; if anything fails, none are deleted."""
        for user in candidates:
            AuditLogEntry.objects.create(
                actor=None,
                action=AuditLogEntry.Action.DELETE_USER,
                target_user_id=str(user.id),
                target_user_name=user.name,
                details=f"Removed by prune_users ({self.describe_data(user) or 'no data'}).",
            )
            user.delete()
