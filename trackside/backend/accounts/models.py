"""
Trackside — Custom User Model.

UUID primary keys, role-based access (admin/coach/driver), and email-based login.
No public registration — all accounts are created by the Admin.
"""

import random
import re
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from accounts.managers import UserManager


# A driver's short display ID: "D" and 5 digits (for example D17256). It is NOT a login identifier.
DRIVER_CODE_PATTERN = r"^D[0-9]{5}$"
DRIVER_CODE_RULE = "A driver ID is the letter D followed by 5 digits, for example D17256."
CODE_TRIES = 50


def next_driver_code() -> str:
    """A random driver code from D10000 to D99999 that nobody has yet; a clear error after 50 tries."""
    for _ in range(CODE_TRIES):
        code = f"D{random.SystemRandom().randint(10000, 99999)}"
        if not User.objects.filter(driver_code=code).exists():
            return code
    raise RuntimeError("Could not find an unused driver ID after 50 tries; too many drivers already have one.")


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

    username = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text="System-generated unique login identifier (e.g. TRK-DRV-000042)",
    )

    # Login also accepts this short ID (see LoginView); the help text below is kept as is to avoid a migration
    driver_code = models.CharField(
        max_length=6,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(DRIVER_CODE_PATTERN, DRIVER_CODE_RULE)],
        help_text="Short display ID for drivers only (D plus 5 digits, e.g. D17256). Not a login identifier.",
    )

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        help_text="Email address — optional for Drivers, required for Coach/Admin",
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

    # Phase 2.0: consent for phone-sensor and biometric data (drivers only); null = not recorded
    consent_recorded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the academy recorded this driver's consent to phone-sensor and biometric data",
    )

    is_under_18 = models.BooleanField(
        default=False,
        help_text="Driver is under 18 (the academy then needs a parent's consent before recording it)",
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

    def save(self, *args, **kwargs):
        """Drivers always have a driver code (made when missing); Admin and Coach never have one."""
        before = self.driver_code
        if self.role == self.Role.DRIVER:
            self.driver_code = self.driver_code or next_driver_code()
        else:
            self.driver_code = None
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and self.driver_code != before:
            kwargs["update_fields"] = list(update_fields) + ["driver_code"]
        super().save(*args, **kwargs)


class AuditLogEntry(models.Model):
    """
    Audit log entry recording admin actions on user accounts.

    Tracks who performed the action, action type, target user, and timestamp.
    """

    class Action(models.TextChoices):
        CREATE_USER = "CREATE_USER", "Create User"
        UPDATE_USER = "UPDATE_USER", "Update User"
        DEACTIVATE_USER = "DEACTIVATE_USER", "Deactivate User"
        REACTIVATE_USER = "REACTIVATE_USER", "Reactivate User"
        DELETE_USER = "DELETE_USER", "Delete User"

    Action.SIMULATOR_START = "SIMULATOR_START"
    # Phase 2.0 actions (kept apart from the lines below so branches merge cleanly)
    Action.CONSENT_CHANGED = "CONSENT_CHANGED"
    Action.SETTINGS_CHANGED = "SETTINGS_CHANGED"
    Action.SIMULATOR_STOP = "SIMULATOR_STOP"
    Action.DEVICE_ASSIGNED = "DEVICE_ASSIGNED"
    Action.DEVICE_UNASSIGNED = "DEVICE_UNASSIGNED"


    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
        help_text="The admin user who initiated this modification",
    )

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
        help_text="Type of action performed",
    )

    target_user_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="ID of the modified user",
    )

    target_user_name = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Display name of the target user",
    )

    details = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description of changes made",
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the modification occurred",
    )

    class Meta:
        db_table = "audit_log_entries"
        ordering = ["-timestamp"]

    def __str__(self):
        actor_str = self.actor.name if self.actor else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {actor_str} -> {self.action} on {self.target_user_name}"

