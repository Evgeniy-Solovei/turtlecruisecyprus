from django.core.management.base import BaseCommand

MIN_IMPORTED_BODY = 2000


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

            from apps.cms.models import SitePage

            home = SitePage.objects.filter(slug="", locale="en").first()
            home_len = len((home.body_html or "") if home else "")
            self.stdout.write(f"Home CMS body: {home_len} chars")
            if home_len < MIN_IMPORTED_BODY:
                dump = Path("/tmp/dump.sql")
                if dump.is_file():
                    self.stdout.write("Running import_wp_site (home content missing)...")
                    from django.core.management import call_command

                    call_command("import_wp_site", sql=str(dump))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "Home uses git template — copy dump to /tmp/dump.sql to auto-import."
                        )
                    )

            media_wp = Path(settings.MEDIA_ROOT) / "wp"
            if media_wp.is_dir():
                count = sum(1 for _ in media_wp.rglob("*") if _.is_file())
                self.stdout.write(f"Media files: {count}")
            else:
                self.stdout.write(self.style.WARNING("media/wp missing — git pull backend/media"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Media check skipped: {exc}"))
