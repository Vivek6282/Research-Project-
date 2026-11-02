"""Remove the locked built-in Demo Circuit.

Nothing is destroyed: a built-in map that nobody used is deleted; one that has sessions or driver
limits is only unlocked (an ordinary map you can archive or delete like any other).
"""

from django.db import migrations, models


def unlock_or_delete_builtin(apps, schema_editor):
    """Delete an unused built-in map; unlock one that has history."""
    Track = apps.get_model("tracks", "Track")
    Session = apps.get_model("driving_sessions", "Session")
    Threshold = apps.get_model("drivers", "DriverZoneThreshold")
    for track in Track.objects.filter(models.Q(is_builtin=True) | models.Q(source="builtin")):
        if Session.objects.filter(track=track).exists() or Threshold.objects.filter(zone__track=track).exists():
            track.is_builtin = False
            track.source = "manual"
            track.save(update_fields=["is_builtin", "source"])
        else:
            track.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tracks", "0007_track_source_drawn"),
        ("driving_sessions", "0003_session_is_demo"),
        ("drivers", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(unlock_or_delete_builtin, migrations.RunPython.noop),
        migrations.RemoveField(model_name="track", name="is_builtin"),
        migrations.AlterField(
            model_name="track",
            name="source",
            field=models.CharField(
                choices=[
                    ("manual", "Added by hand"),
                    ("racechrono_csv", "RaceChrono CSV"),
                    ("vbo", "Racelogic VBO"),
                    ("drawn", "Drawn on the map"),
                ],
                default="manual",
                help_text="Where the track shape came from",
                max_length=20,
            ),
        ),
    ]
