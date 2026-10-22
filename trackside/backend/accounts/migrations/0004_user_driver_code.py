"""
Trackside — Add User.driver_code and give every existing driver a unique code.
"""

import random

import django.core.validators
from django.db import migrations, models


def give_existing_drivers_a_code(apps, schema_editor):
    """Every existing driver without a code gets a random unused one (D10000 to D99999)."""
    User = apps.get_model("accounts", "User")
    taken = set(User.objects.exclude(driver_code=None).values_list("driver_code", flat=True))
    rng = random.SystemRandom()
    for driver in User.objects.filter(role="driver", driver_code=None):
        for _ in range(1000):
            code = f"D{rng.randint(10000, 99999)}"
            if code not in taken:
                break
        else:
            raise RuntimeError("No unused driver ID left to give existing drivers.")
        taken.add(code)
        User.objects.filter(pk=driver.pk).update(driver_code=code)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_auditlogentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="driver_code",
            field=models.CharField(
                blank=True, max_length=6, null=True, unique=True,
                validators=[django.core.validators.RegexValidator("^D[0-9]{5}$", "A driver ID is the letter D followed by 5 digits, for example D17256.")],
                help_text="Short display ID for drivers only (D plus 5 digits, e.g. D17256). Not a login identifier.",
            ),
        ),
        migrations.RunPython(give_existing_drivers_a_code, migrations.RunPython.noop),
    ]
