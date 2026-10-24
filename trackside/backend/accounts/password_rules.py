"""
Trackside Accounts — Password strength rules for accounts created or changed by the admin.

Runs Django's configured validators (AUTH_PASSWORD_VALIDATORS: minimum length,
common passwords, all-numeric, too similar to the name or email) and turns
their messages into a normal field error.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


def check_password_strength(password: str, name: str = "", email: str = "", existing_user=None) -> None:
    """Raise a "password" field error listing every rule the password breaks."""
    candidate = existing_user if existing_user is not None else get_user_model()(name=name or "", email=email or None)
    if existing_user is not None:
        # Compare with the values being saved, not only the old ones
        candidate.name = name or existing_user.name
        candidate.email = email if email is not None else existing_user.email
    try:
        validate_password(password, user=candidate)
    except DjangoValidationError as error:
        raise serializers.ValidationError({"password": list(error.messages)})
