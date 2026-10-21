"""Trackside — Devices serializers."""

from django.db import transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model
from devices.models import Device, DeviceCommand

User = get_user_model()


class DeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for IoT devices.
    Returns raw_api_key ONCE on creation to the Admin, never on subsequent reads.
    Enforces driver assignment validation and one-device-per-type constraint atomically.
    """

    assigned_to_name = serializers.SerializerMethodField()
    is_online = serializers.BooleanField(read_only=True)
    raw_api_key = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Device
        fields = [
            "id", "device_type", "name", "assigned_to", "assigned_to_name",
            "status", "last_seen_at", "is_online", "raw_api_key",
        ]
        read_only_fields = ["id", "name", "last_seen_at", "is_online", "raw_api_key"]

    def get_assigned_to_name(self, obj):
        """
        Get display name of the assigned user.
        Input: Device instance.
        Output: User display name or None.
        """
        return obj.assigned_to.name if obj.assigned_to else None

    def validate_assigned_to(self, value):
        """
        Validate that assigned_to is an active driver or unassigned.
        Input: User instance or None.
        Output: Validated User instance or None.
        """
        if value is None:
            return None
        if value.role != "driver":
            raise serializers.ValidationError(
                f"Cannot assign device to user '{value.name}' with role '{value.role}'. Devices can only be assigned to drivers."
            )
        if not value.is_active:
            raise serializers.ValidationError(
                f"Cannot assign device to deactivated driver '{value.name}'."
            )
        return value

    def create(self, validated_data):
        """
        Create a new device and generate an API key.
        Input: Validated data dictionary.
        Output: Created Device instance with ephemeral raw_api_key.
        """
        instance = super().create(validated_data)
        raw_token = instance.set_api_key()
        instance.save(update_fields=["api_key_hash"])
        instance._raw_api_key = raw_token
        return instance

    def update(self, instance, validated_data):
        """
        Update device fields. Enforces one-device-per-type rule atomically.
        Input: Device instance and validated data dictionary.
        Output: Updated Device instance.
        """
        if "assigned_to" in validated_data:
            target_driver = validated_data.get("assigned_to")
            with transaction.atomic():
                # Lock target device row
                locked_device = Device.objects.select_for_update().get(pk=instance.pk)
                old_driver = locked_device.assigned_to
                displaced_device = None
                displaced_prev_driver = None

                if target_driver is not None and target_driver != old_driver:
                    # Check if target driver already holds a device of this type
                    conflict = (
                        Device.objects.select_for_update()
                        .filter(assigned_to=target_driver, device_type=locked_device.device_type)
                        .exclude(pk=locked_device.pk)
                        .first()
                    )
                    if conflict:
                        displaced_device = conflict
                        displaced_prev_driver = conflict.assigned_to
                        conflict.assigned_to = None
                        conflict.save(update_fields=["assigned_to"])

                for attr, val in validated_data.items():
                    setattr(locked_device, attr, val)
                locked_device.save()

                # Build reassignment notice
                notice = None
                if old_driver and target_driver and old_driver != target_driver:
                    dev_label = locked_device.get_device_type_display()
                    notice = f"{dev_label} was moved from {old_driver.name}"
                elif displaced_device and displaced_prev_driver:
                    dev_label = displaced_device.get_device_type_display()
                    notice = f"{dev_label} was moved from {displaced_prev_driver.name}"
                elif target_driver and not old_driver:
                    dev_label = locked_device.get_device_type_display()
                    notice = f"{dev_label} assigned to {target_driver.name}"
                elif not target_driver and old_driver:
                    dev_label = locked_device.get_device_type_display()
                    notice = f"{dev_label} unassigned from {old_driver.name}"

                # Write audit log entries (D2)
                request = self.context.get("request")
                actor = (
                    request.user
                    if request and hasattr(request, "user") and request.user.is_authenticated
                    else None
                )
                from accounts.models import AuditLogEntry

                if target_driver != old_driver:
                    prev_name = old_driver.name if old_driver else "Unassigned"
                    new_name = target_driver.name if target_driver else "Unassigned"
                    assign_action = (
                        AuditLogEntry.Action.DEVICE_ASSIGNED
                        if target_driver
                        else AuditLogEntry.Action.DEVICE_UNASSIGNED
                    )
                    AuditLogEntry.objects.create(
                        actor=actor,
                        action=assign_action,
                        target_user_id=str(target_driver.id) if target_driver else (str(old_driver.id) if old_driver else None),
                        target_user_name=new_name if target_driver else prev_name,
                        details=(
                            f"Device {locked_device.id} ({locked_device.device_type}) assigned: "
                            f"previous driver '{prev_name}', new driver '{new_name}'"
                        ),
                    )

                if displaced_device:
                    displaced_prev_name = (
                        displaced_prev_driver.name if displaced_prev_driver else "Unassigned"
                    )
                    AuditLogEntry.objects.create(
                        actor=actor,
                        action=AuditLogEntry.Action.DEVICE_UNASSIGNED,
                        target_user_id=str(displaced_prev_driver.id) if displaced_prev_driver else None,
                        target_user_name=displaced_prev_name,
                        details=(
                            f"Device {displaced_device.id} ({displaced_device.device_type}) unassigned due to one-per-type move: "
                            f"previous driver '{displaced_prev_name}', new driver 'Unassigned'"
                        ),
                    )

                locked_device._displaced_device = displaced_device
                locked_device._displaced_prev_driver = displaced_prev_driver
                locked_device._old_driver = old_driver
                locked_device._reassignment_notice = notice

                return locked_device

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """
        Serialize device fields to representation dictionary.
        Input: Device instance.
        Output: Serialized dictionary.
        """
        ret = super().to_representation(instance)
        # Only include raw_api_key once when created
        if hasattr(instance, "_raw_api_key"):
            ret["raw_api_key"] = instance._raw_api_key
        else:
            ret.pop("raw_api_key", None)

        if hasattr(instance, "_reassignment_notice") and instance._reassignment_notice:
            ret["reassignment_notice"] = instance._reassignment_notice
        return ret

class DeviceCommandSerializer(serializers.ModelSerializer):
    """Serializer for IoT device diagnostic commands."""
    
    requested_by_name = serializers.CharField(source="requested_by.name", read_only=True)

    class Meta:
        model = DeviceCommand
        fields = [
            "id",
            "device",
            "command_type",
            "status",
            "requested_by",
            "requested_by_name",
            "requested_at",
            "completed_at",
            "result",
        ]
        read_only_fields = [
            "id",
            "device",
            "status",
            "requested_by",
            "requested_by_name",
            "requested_at",
            "completed_at",
            "result",
        ]
