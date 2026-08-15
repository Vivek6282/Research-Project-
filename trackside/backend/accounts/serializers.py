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

    Exposes id, username, email, name, role, is_active, created_at, and created_by.
    Password is explicitly excluded — it should never appear in any response.
    """

    created_by_name = serializers.SerializerMethodField(
        help_text="Display name of the admin who created this account",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
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
    Username is automatically generated server-side.
    """

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Email address — required for Coach accounts, optional for Drivers",
    )

    username = serializers.CharField(
        read_only=True,
        help_text="System-generated unique identifier (e.g. TRK-DRV-000042)",
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Raw password — will be hashed, never stored in plain text",
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "name", "role", "password", "is_active"]
        read_only_fields = ["id", "username"]

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

    def validate(self, attrs):
        """
        Validate email requirements based on role.
        Email is required for Coach, optional for Driver.
        """
        role = attrs.get("role")
        email = attrs.get("email")

        if role == "coach" and not email:
            raise serializers.ValidationError({"email": "Email address is required for Coach accounts."})

        if role == "driver" and email == "":
            attrs["email"] = None

        return attrs

    def create(self, validated_data):
        """
        Create a new user with a properly hashed password and server-generated username.
        The requesting admin is recorded as created_by.
        """
        # Strictly ignore any client-supplied username
        validated_data.pop("username", None)

        role = validated_data.get("role", "driver")
        role_code_map = {"driver": "DRV", "coach": "COACH", "admin": "ADMIN"}
        role_code = role_code_map.get(role.lower(), role.upper())

        # Auto-generate role-scoped username sequence TRK-{ROLE}-{6-digit}
        count = User.objects.filter(role=role).count() + 1
        while True:
            candidate = f"TRK-{role_code}-{count:06d}"
            if not User.objects.filter(username=candidate).exists():
                username = candidate
                break
            count += 1

        validated_data["username"] = username
        password = validated_data.pop("password")
        request = self.context.get("request")

        user = User(
            **validated_data,
            created_by=request.user if request else None,
        )
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing user accounts (Admin-only).

    Allows updating name, email, role, and is_active status.
    Password updates are handled separately to ensure proper hashing.
    """

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Email address — required for Coach accounts, optional for Drivers",
    )

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
        fields = ["id", "username", "email", "name", "role", "is_active", "password"]
        read_only_fields = ["id", "username"]

    def validate_role(self, value):
        """Prevent role escalation to admin via the API."""
        if value == "admin" and (not self.instance or self.instance.role != "admin"):
            raise serializers.ValidationError(
                "Cannot change role to admin through the API."
            )
        return value

    def validate(self, attrs):
        """
        Validate email requirements based on role and prevent self-deactivation.
        Email is required for Coach, optional for Driver.
        """
        role = attrs.get("role", self.instance.role if self.instance else None)
        email = attrs.get("email")

        # Prevent self-deactivation by the logged-in admin user
        request = self.context.get("request")
        if request and request.user and self.instance and self.instance == request.user:
            if attrs.get("is_active") is False:
                raise serializers.ValidationError({"is_active": "You cannot deactivate your own admin account."})

        if role == "coach" and email is not None and not email:
            raise serializers.ValidationError({"email": "Email address is required for Coach accounts."})

        if role == "driver" and email == "":
            attrs["email"] = None

        return attrs

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

    Validates identifier (email or Driver ID username) and password fields.
    """

    identifier = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="User's email address or Driver ID (username)",
    )
    email = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Email address or Driver ID (alias)",
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="User's password — never logged",
    )

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError({"identifier": "Email or Driver ID is required."})
        attrs["identifier"] = identifier
        return attrs


from accounts.models import AuditLogEntry


class AuditLogEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for returning audit log entries to the frontend.
    """

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLogEntry
        fields = [
            "id",
            "actor",
            "actor_name",
            "action",
            "target_user_id",
            "target_user_name",
            "details",
            "timestamp",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.name
        return "System Admin"

