"""
Trackside — Account serializers.

Handles user data serialization for API responses and user creation.
Requirement #8: password is never included in responses or logged.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for user data returned in API responses.

    Exposes id, email, name, role, is_active, created_at, and created_by.
    Password is explicitly excluded — it should never appear in any response.
    """

    created_by_name = serializers.SerializerMethodField(
        help_text="Display name of the admin who created this account",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "is_active",
            "created_at",
            "created_by",
            "created_by_name",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        """Return the name of the admin who created this user, or None."""
        if obj.created_by:
            return obj.created_by.name
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer for Admin-only user creation (POST /api/users/).

    Accepts email, name, role, and password. The password field is
    write-only — it's hashed via set_password() and never returned.
    Requirement #8: never log request.data on this endpoint.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Raw password — will be hashed, never stored in plain text",
    )

    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "password", "is_active"]
        read_only_fields = ["id"]

    def validate_role(self, value):
        """
        Prevent creating additional admin accounts through the API.
        The seeded admin is the only admin — additional admins must be
        created through the management command if ever needed.
        """
        if value == "admin":
            raise serializers.ValidationError(
                "Admin accounts cannot be created through the API. "
                "Use the seed_admin management command."
            )
        return value

    def create(self, validated_data):
        """
        Create a new user with a properly hashed password.
        The requesting admin is recorded as created_by.
        """
        password = validated_data.pop("password")
        request = self.context.get("request")

        user = User(
            **validated_data,
            created_by=request.user if request else None,
        )
        # Requirement #8: always use set_password(), never store raw
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing user accounts (Admin-only).

    Allows updating name, email, role, and is_active status.
    Password updates are handled separately to ensure proper hashing.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
        help_text="New password — leave blank to keep current password",
    )

    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "is_active", "password"]
        read_only_fields = ["id"]

    def validate_role(self, value):
        """Prevent role escalation to admin via the API."""
        if value == "admin":
            raise serializers.ValidationError(
                "Cannot change role to admin through the API."
            )
        return value

    def update(self, instance, validated_data):
        """
        Update user fields. If a new password is provided, hash it
        properly via set_password().
        """
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login requests.

    Validates email and password fields. Authentication logic is
    handled in the view — this only validates the input shape.
    """

    email = serializers.EmailField(
        help_text="User's email address",
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="User's password — never logged",
    )
