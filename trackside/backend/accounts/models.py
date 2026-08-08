"""
Trackside — Custom User Model.

UUID primary keys, role-based access (admin/coach/driver), and email-based login.
No public registration — all accounts are created by the Admin.
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for Trackside.

    Uses email (not username) as the login identifier.
    Role determines dashboard access and API permissions.
    Accounts are only created by the Admin — no self-registration.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        COACH = "coach", "Coach"
        DRIVER = "driver", "Driver"

    # UUID primary key per schema requirement
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this user",
    )

    email = models.EmailField(
        unique=True,
        help_text="Email address — used as the login identifier",
    )

    name = models.CharField(
        max_length=150,
        help_text="Display name shown in the UI",
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        help_text="Determines which dashboard and API endpoints the user can access",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Deactivated users cannot log in. Admin can deactivate accounts.",
    )

    # Django compatibility flags — not used for Trackside role checks
    is_staff = models.BooleanField(
        default=False,
        help_text="Django admin site access flag — not used in Trackside's own auth",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this account was created",
    )

    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
        help_text="The admin who created this account (null for the seeded admin)",
    )

    objects = UserManager()

    # Email is the login field, not username
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.role})"
