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

            from apps.cms.models import SiteConfig, SitePage

            home = SitePage.objects.filter(slug="", locale="en").first()
            home_len = len((home.body_html or "") if home else "")
            self.stdout.write(f"Home CMS body: {home_len} chars")
            footer_row = SiteConfig.objects.filter(key="footer").first()
            footer_ok = bool(footer_row and (footer_row.value or {}).get("en", {}).get("title"))
            if not footer_ok:
                self.stdout.write("Importing footer/socials from prod...")
                from apps.cms.importers.live import import_live_site_config

                import_live_site_config()
            if home_len < MIN_IMPORTED_BODY:
                dump = Path(settings.WP_SQL_DUMP_PATH) if hasattr(settings, "WP_SQL_DUMP_PATH") else None
                if not dump or not dump.is_file():
                    dump = Path("/tmp/dump.sql")
                if dump.is_file():
                    self.stdout.write(f"Running import_wp_site from {dump}...")
                    from django.core.management import call_command

                    call_command("import_wp_site", sql=str(dump))
                    call_command("sync_wp_media")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "CMS empty and no SQL dump found. "
                            f"Set WP_SQL_DUMP_PATH or copy dump to /tmp/dump.sql. "
                            "Fallback: python manage.py import_wp_live"
                        )
                    )

            media_wp = Path(settings.MEDIA_ROOT) / "wp"
            if media_wp.is_dir():
                count = sum(1 for _ in media_wp.rglob("*") if _.is_file())
                self.stdout.write(f"Media files: {count}")
                if count < 100:
                    from django.core.management import call_command

                    self.stdout.write(self.style.WARNING("Few media files — syncing WP uploads..."))
                    try:
                        call_command("sync_wp_media")
                    except Exception as sync_exc:
                        self.stdout.write(
                            self.style.WARNING(
                                f"sync_wp_media skipped: {sync_exc}. "
                                "Copy wp-content/uploads from the full dump to the server."
                            )
                        )
            else:
                self.stdout.write(self.style.WARNING("media/wp missing — run sync_wp_media"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Media check skipped: {exc}"))
