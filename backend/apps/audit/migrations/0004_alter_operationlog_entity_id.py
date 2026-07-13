from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0003_drop_settings_app_table"),
    ]

    operations = [
        migrations.AlterField(
            model_name="operationlog",
            name="entity_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=128,
                verbose_name="ID сущности",
            ),
        ),
    ]
