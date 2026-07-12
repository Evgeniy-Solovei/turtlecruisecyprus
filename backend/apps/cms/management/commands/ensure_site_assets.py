from django.core.management.base import BaseCommand

from apps.cms.asset_urls import normalize_footer_config
from apps.cms.models import SiteConfig


class Command(BaseCommand):
    help = "One-time deploy hook: fix footer asset URLs and verify media folder."

    def handle(self, *args, **options):
        row = SiteConfig.objects.filter(key="footer").first()
        if row:
            fixed = normalize_footer_config(row.value)
            if fixed != row.value:
                row.value = fixed
                row.save(update_fields=["value"])
                self.stdout.write(self.style.SUCCESS("Footer icons → static paths."))
            else:
                self.stdout.write("Footer icons already OK.")

        from pathlib import Path

        from django.conf import settings

        media_wp = Path(settings.MEDIA_ROOT) / "wp"
        if media_wp.is_dir():
            count = sum(1 for _ in media_wp.rglob("*") if _.is_file())
            self.stdout.write(f"Media files: {count}")
            if count < 100:
                self.stdout.write(
                    self.style.WARNING(
                        "Few media files — run git pull (backend/media is in repo)."
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING("media/wp missing — run git pull and docker compose up -d --build")
            )
