"""Trackside — Serializers for academy settings and driver consent."""

from django.utils import timezone
from rest_framework import serializers

from academy.models import AcademySettings


class AcademySettingsSerializer(serializers.ModelSerializer):
    """Retention period (1 to 120 months) and who changed it last."""

    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AcademySettings
        fields = ["retention_months", "updated_at", "updated_by_name"]
        read_only_fields = ["updated_at", "updated_by_name"]

    def get_updated_by_name(self, obj):
        """Display name of the admin who last saved the settings, or None."""
        return obj.updated_by.name if obj.updated_by else None


class DriverConsentSerializer(serializers.Serializer):
    """Consent and age flags of one driver; consent_recorded=true stamps the time it was recorded."""

    consent_recorded = serializers.BooleanField(required=False)
    consent_recorded_at = serializers.DateTimeField(read_only=True)
    is_under_18 = serializers.BooleanField(required=False)

    def to_representation(self, driver):
        """The driver's current flags."""
        return {"consent_recorded": driver.consent_recorded_at is not None,
                "consent_recorded_at": driver.consent_recorded_at, "is_under_18": driver.is_under_18}

    def update(self, driver, validated_data):
        """Record or withdraw consent and set the under-18 flag."""
        if "consent_recorded" in validated_data:
            recorded = validated_data["consent_recorded"]
            if recorded and driver.consent_recorded_at is None:
                driver.consent_recorded_at = timezone.now()
            elif not recorded:
                driver.consent_recorded_at = None
        if "is_under_18" in validated_data:
            driver.is_under_18 = validated_data["is_under_18"]
        driver.save(update_fields=["consent_recorded_at", "is_under_18"])
        return driver
