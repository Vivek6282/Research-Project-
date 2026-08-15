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

    username = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text="System-generated unique login identifier (e.g. TRK-DRV-000042)",
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

    objects = UserManager()

    # Email is the login field, not username
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.role})"


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

