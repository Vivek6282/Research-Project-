"""
Trackside — set_driver_identity management command.

Sets the display name and/or the driver ID (for example D17256) of ONE driver. It changes
nothing else: sessions, readings and every other record are left alone.

Examples:
    python manage.py set_driver_identity --email marco@x.com --new-name "Marco Ferrati" --code D17256
    python manage.py set_driver_identity --name "Old Mock Name" --new-name "Anaya Iyer"

Run it only after a backup of the database.
"""

import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.functions import Lower, Trim

from accounts.models import DRIVER_CODE_PATTERN, DRIVER_CODE_RULE, AuditLogEntry, next_driver_code

User = get_user_model()


class Command(BaseCommand):
    help = "Set the name and/or driver ID (D plus 5 digits) of exactly one driver. Nothing else is changed."

    def add_arguments(self, parser):
        who = parser.add_mutually_exclusive_group(required=True)
        who.add_argument("--email", help="Email of the driver to change.")
        who.add_argument("--username", help="Login name of the driver to change (e.g. TRK-DRV-000042).")
        who.add_argument("--name", help="Current full name of the driver (ignores case and surrounding spaces).")
        parser.add_argument("--new-name", help="The name to set.")
        parser.add_argument("--code", help="The driver ID to set, for example D17256.")

    def handle(self, *args, **options):
        driver = self.find_driver(options)
        new_name = (options["new_name"] or "").strip() or None
        code = (options["code"] or "").strip() or None
        if code:
            self.check_code(code, driver)
        before = self.describe(driver)

        with transaction.atomic():
            if new_name:
                driver.name = new_name
            if code:
                driver.driver_code = code
            elif not driver.driver_code:
                driver.driver_code = next_driver_code()
            driver.save()
            AuditLogEntry.objects.create(
                actor=None,
                action=AuditLogEntry.Action.UPDATE_USER,
                target_user_id=str(driver.id),
                target_user_name=driver.name,
                details=f"set_driver_identity: {before} -> {self.describe(driver)}",
            )
        self.stdout.write(f"Before: {before}")
        self.stdout.write(self.style.SUCCESS(f"After:  {self.describe(driver)}"))

    @staticmethod
    def describe(user) -> str:
        """'name=... code=... email=... username=...' of a user."""
        return f"name={user.name!r} code={user.driver_code or '-'} email={user.email or '-'} username={user.username or '-'}"

    @staticmethod
    def find_driver(options):
        """The one driver the options point to; a clear error (and no change) for none or several."""
        users = User.objects.filter(role=User.Role.DRIVER)
        if options["email"]:
            matches = list(users.filter(email__iexact=options["email"].strip()))
        elif options["username"]:
            matches = list(users.filter(username=options["username"].strip()))
        else:
            matches = list(users.annotate(clean_name=Lower(Trim("name"))).filter(clean_name=options["name"].strip().lower()))
        if len(matches) != 1:
            raise CommandError(f"That matched {len(matches)} drivers; it must match exactly one. Nothing was changed.")
        return matches[0]

    @staticmethod
    def check_code(code, driver):
        """The code must look like D17256 and not belong to another user."""
        if not re.match(DRIVER_CODE_PATTERN, code):
            raise CommandError(DRIVER_CODE_RULE)
        if User.objects.filter(driver_code=code).exclude(pk=driver.pk).exists():
            raise CommandError(f"{code} is already used by another driver.")
