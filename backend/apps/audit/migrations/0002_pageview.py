from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PageView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("view_id", models.CharField(db_index=True, max_length=64, verbose_name="ID просмотра")),
                ("path", models.CharField(db_index=True, max_length=500, verbose_name="Путь")),
                ("page_title", models.CharField(blank=True, max_length=255, verbose_name="Заголовок")),
                ("locale", models.CharField(blank=True, max_length=8, verbose_name="Язык")),
                ("referrer", models.URLField(blank=True, max_length=500, verbose_name="Referrer")),
                ("duration_ms", models.PositiveIntegerField(default=0, verbose_name="Время на странице, мс")),
                ("scroll_depth_pct", models.PositiveSmallIntegerField(default=0, verbose_name="Глубина скролла, %")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активный просмотр")),
                ("entered_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Вход")),
                ("left_at", models.DateTimeField(blank=True, null=True, verbose_name="Выход")),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="page_views",
                        to="audit.visitorsession",
                        verbose_name="Сессия",
                    ),
                ),
            ],
            options={
                "verbose_name": "Просмотр страницы",
                "verbose_name_plural": "Просмотры страниц",
                "ordering": ["-entered_at"],
                "indexes": [
                    models.Index(fields=["path", "entered_at"], name="audit_pagev_path_6f0f0a_idx"),
                    models.Index(fields=["session", "entered_at"], name="audit_pagev_session_2c2f0a_idx"),
                ],
            },
        ),
    ]
