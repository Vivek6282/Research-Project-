"""
Data and schema migration for Device.status.
Converts any existing rows with status='connected' to 'offline' (no data loss)
and updates the status field choices to [('pairing', 'Pairing'), ('offline', 'Offline')].
"""

from django.db import migrations, models


def set_connected_to_offline(apps, schema_editor):
    """
    Data migration: sets existing connected rows to offline.
    """
    Device = apps.get_model("devices", "Device")
    Device.objects.filter(status="connected").update(status="offline")


def reverse_noop(apps, schema_editor):
    """
    Reverse migration no-op.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0003_devicecommand"),
    ]

    operations = [
        migrations.RunPython(set_connected_to_offline, reverse_noop),
        migrations.AlterField(
            model_name="device",
            name="status",
            field=models.CharField(
                choices=[("pairing", "Pairing"), ("offline", "Offline")],
                default="offline",
                help_text="Current connection status of the device",
                max_length=15,
            ),
        ),
    ]
