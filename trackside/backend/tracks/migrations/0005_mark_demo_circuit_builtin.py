"""Data migration: the existing Demo Circuit becomes the locked built-in track."""

from django.db import migrations


def mark_demo_circuit_builtin(apps, schema_editor):
    """Set is_builtin and source on the track named 'Demo Circuit', if it exists."""
    Track = apps.get_model("tracks", "Track")
    Track.objects.filter(name="Demo Circuit").update(is_builtin=True, source="builtin")


def unmark_demo_circuit_builtin(apps, schema_editor):
    """Undo: clear the built-in flag and go back to the default source."""
    Track = apps.get_model("tracks", "Track")
    Track.objects.filter(name="Demo Circuit").update(is_builtin=False, source="manual")


class Migration(migrations.Migration):

    dependencies = [
        ("tracks", "0004_track_builtin_archived_source"),
    ]

    operations = [
        migrations.RunPython(mark_demo_circuit_builtin, unmark_demo_circuit_builtin),
    ]
