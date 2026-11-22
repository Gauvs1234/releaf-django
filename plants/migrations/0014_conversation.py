import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def group_existing_messages_into_conversations(apps, schema_editor):
    Conversation = apps.get_model("plants", "Conversation")
    Message = apps.get_model("plants", "Message")
    database = schema_editor.connection.alias

    messages_without_conversation = (
        Message.objects.using(database)
        .filter(conversation__isnull=True)
        .order_by("pk")
    )
    for message in messages_without_conversation.iterator():
        participant_one_id, participant_two_id = sorted(
            (message.sender_id, message.receiver_id)
        )
        conversation, _ = Conversation.objects.using(database).get_or_create(
            participant_one_id=participant_one_id,
            participant_two_id=participant_two_id,
            plant_id=None,
        )
        Message.objects.using(database).filter(pk=message.pk).update(
            conversation_id=conversation.pk
        )


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0013_favorite"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "participant_one",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations_as_one",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "participant_two",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations_as_two",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "plant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations",
                        to="plants.plant",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("participant_one", "participant_two", "plant"),
                        name="unique_participants_plant_conversation",
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name="message",
            name="conversation",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="plants.conversation",
            ),
        ),
        migrations.RunPython(
            group_existing_messages_into_conversations,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="message",
            name="conversation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="plants.conversation",
            ),
        ),
    ]
