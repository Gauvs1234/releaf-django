from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_existing_plants_to_only_user(apps, schema_editor):
    Plant = apps.get_model("plants", "Plant")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    plants_without_owner = Plant.objects.using(schema_editor.connection.alias).filter(
        owner__isnull=True
    )

    if not plants_without_owner.exists():
        return

    users = User.objects.using(schema_editor.connection.alias).order_by("pk")
    if users.count() != 1:
        raise RuntimeError(
            "Cannot assign existing plants automatically: expected exactly one "
            "user, found a different number. Assign each existing plant an owner "
            "before applying this migration."
        )

    plants_without_owner.update(owner=users.first().pk)


def clear_existing_plant_owners(apps, schema_editor):
    Plant = apps.get_model("plants", "Plant")
    Plant.objects.using(schema_editor.connection.alias).update(owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0003_plant_care_level"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="plant",
            name="owner",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="plants",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            assign_existing_plants_to_only_user,
            clear_existing_plant_owners,
        ),
        migrations.AlterField(
            model_name="plant",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="plants",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
