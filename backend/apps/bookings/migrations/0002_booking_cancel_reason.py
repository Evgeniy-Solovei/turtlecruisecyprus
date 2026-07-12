from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="cancel_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("sold_out", "Места закончились"),
                    ("hold_expired", "Истекло удержание"),
                    ("user_cancelled", "Отменено пользователем"),
                ],
                max_length=32,
                verbose_name="Причина отмены/истечения",
            ),
        ),
    ]
