from django.db import migrations, models
import django.db.models.deletion


def ensure_no_unlinked_reviews(apps, schema_editor):
    Review = apps.get_model("plants", "Review")
    if Review.objects.using(schema_editor.connection.alias).exists():
        raise RuntimeError(
            "Cannot add the plant relationship because existing reviews are not "
            "linked to plants. Assign a plant to each review, then apply this migration."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0006_contactmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="plant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews",
                to="plants.plant",
            ),
        ),
        migrations.RunPython(
            ensure_no_unlinked_reviews,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="review",
            name="plant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews",
                to="plants.plant",
            ),
        ),
    ]
