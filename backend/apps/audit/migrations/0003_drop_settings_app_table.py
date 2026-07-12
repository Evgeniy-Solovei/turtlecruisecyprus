from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_pageview"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS settings_app_setting;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DELETE FROM django_migrations WHERE app = 'settings_app';",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
