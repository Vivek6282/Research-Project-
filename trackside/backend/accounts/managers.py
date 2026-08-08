"""
Trackside — Custom User Manager.

Handles user creation with mandatory email, role, and proper password hashing.
Requirement #8: always uses set_password() / check_password(), never manual hashing.
"""

import uuid
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom manager for the Trackside User model.
    All user creation goes through here to guarantee password hashing
    and required field validation.
    """

    def create_user(self, email, name, role, password=None, **extra_fields):
        """
        Create a standard user (Coach or Driver).

        Args:
            email: unique email address — used as the login identifier.
            name: display name for the user.
            role: one of 'admin', 'coach', 'driver'.
            password: raw password — will be hashed via set_password().
            **extra_fields: additional model fields (e.g. created_by).

        Returns:
            The newly created User instance with a hashed password.

        Raises:
            ValueError: if email or role is missing.
        """
        if not email:
            raise ValueError("Users must have an email address")
        if not role:
            raise ValueError("Users must have a role assigned")

        email = self.normalize_email(email)
        user = self.model(
            id=uuid.uuid4(),
            email=email,
            name=name,
            role=role,
            **extra_fields,
        )
        # Requirement #8: set_password() hashes via PBKDF2-SHA256
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        """
        Create an admin-level superuser.

        Used by the seed_admin management command. Forces role='admin'
        and sets Django's is_staff/is_superuser flags for compatibility
        with any Django admin tooling if ever enabled.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(
            email=email,
            name=name,
            role="admin",
            password=password,
            **extra_fields,
        )
