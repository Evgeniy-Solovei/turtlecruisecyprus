from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deploy hook: fix footer asset URLs and verify media folder."

    def handle(self, *args, **options):
        try:
            from apps.cms.asset_urls import normalize_footer_config
            from apps.cms.models import SiteConfig

            row = SiteConfig.objects.filter(key="footer").first()
            if row:
                fixed = normalize_footer_config(row.value)
                if fixed != row.value:
                    row.value = fixed
                    row.save(update_fields=["value"])
                    self.stdout.write(self.style.SUCCESS("Footer icons → static paths."))
                else:
                    self.stdout.write("Footer icons already OK.")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Footer fix skipped: {exc}"))

        try:
            from pathlib import Path

            from django.conf import settings

            media_wp = Path(settings.MEDIA_ROOT) / "wp"
            if media_wp.is_dir():
                count = sum(1 for _ in media_wp.rglob("*") if _.is_file())
                self.stdout.write(f"Media files: {count}")
            else:
                self.stdout.write(self.style.WARNING("media/wp missing — git pull backend/media"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Media check skipped: {exc}"))
