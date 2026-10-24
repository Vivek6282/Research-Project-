"""
Trackside Accounts — Login request serializer.

Validates the identifier (email, long username or short driver ID) and the
password. Both have a maximum length, so an oversized body cannot make the
server hash megabytes of text.
"""

from rest_framework import serializers

MAX_IDENTIFIER_LENGTH = 254   # the longest valid email address
MAX_PASSWORD_LENGTH = 256


class LoginSerializer(serializers.Serializer):
    """Identifier (or its alias "email") and password, both required and length-limited."""

    identifier = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=MAX_IDENTIFIER_LENGTH,
        help_text="User's email address or Driver ID (username)",
    )
    email = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=MAX_IDENTIFIER_LENGTH,
        help_text="Email address or Driver ID (alias)",
    )
    password = serializers.CharField(
        write_only=True,
        max_length=MAX_PASSWORD_LENGTH,
        style={"input_type": "password"},
        help_text="User's password — never logged",
    )

    def validate(self, attrs):
        """Use "identifier", or "email" when only that was sent; one of them is required."""
        identifier = attrs.get("identifier") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError({"identifier": "Email or Driver ID is required."})
        attrs["identifier"] = identifier
        return attrs
