"""
Trackside — seed_admin management command.

Creates the initial Admin account from environment variables.
This is the ONLY way to create an admin — no API endpoint exists for it.

Usage:
    python manage.py seed_admin

Environment variables required:
    ADMIN_EMAIL — the admin's email address
    ADMIN_PASSWORD — the admin's password (will be hashed)
    ADMIN_NAME — display name for the admin (optional, defaults to "Admin")
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Create the initial Admin account from environment variables"

    def handle(self, *args, **options):
        """
        Read admin credentials from environment variables and create the
        admin user if they don't already exist.

        Idempotent: running this multiple times won't create duplicates
        or change the existing admin's password.
        """
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        name = os.environ.get("ADMIN_NAME", "Admin")

        if not email or not password:
            raise CommandError(
                "ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set. "
                "Never hardcode admin credentials in source code."
            )

        # Check if admin already exists — idempotent
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Admin account '{email}' already exists. Skipping creation."
                )
            )
            return

        # Create the admin using the manager, which hashes the password
        user = User.objects.create_superuser(
            email=email,
            name=name,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin account created: {user.email} ({user.name})"
            )
        )
