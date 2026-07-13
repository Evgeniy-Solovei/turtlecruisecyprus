from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="provider_client_secret",
            field=models.CharField(
                blank=True,
                help_text="Не показывать клиенту вне платежного flow.",
                max_length=1024,
                verbose_name="Stripe client secret",
            ),
        ),
    ]
