"""Trackside — Preferences serializers."""

from rest_framework import serializers
from preferences.models import UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for user display preferences.
    User field is read-only — it's set from the requesting user.
    """

    class Meta:
        model = UserPreference
        fields = ["id", "user", "theme", "font_size"]
        read_only_fields = ["id", "user"]
