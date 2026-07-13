from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Deploy hook: load CMS snapshot from git, verify images, fail if not identical to repo."

    def handle(self, *args, **options):
        from pathlib import Path

        from django.conf import settings
        from django.core.management import call_command

        snapshot_path = Path(settings.BASE_DIR) / "cms_snapshot" / "snapshot.json"
        snapshot_required = getattr(settings, "CMS_SNAPSHOT_REQUIRED", False)

        if snapshot_path.is_file():
            self.stdout.write("Loading CMS snapshot from git...")
            call_command("import_cms_snapshot")
        elif snapshot_required:
            raise CommandError(
                "cms_snapshot/snapshot.json is missing. "
                "Run: python manage.py export_cms_snapshot && git add cms_snapshot && git commit"
            )

        try:
            from apps.cms.asset_urls import normalize_footer_config
            from apps.cms.models import SiteConfig

            row = SiteConfig.objects.filter(key="footer").first()
            if row:
                fixed = normalize_footer_config(row.value)
                if fixed != row.value:
                    row.value = fixed
                    row.save(update_fields=["value"])
                    self.stdout.write(self.style.SUCCESS("Footer icons normalized."))
        except Exception as exc:
            raise CommandError(f"Footer config failed: {exc}") from exc

        from apps.cms.site_media import bake_cms_media_urls, vendor_site_media

        vendored = vendor_site_media()
        self.stdout.write(
            f"Site images: referenced={vendored['referenced']} "
            f"copied={vendored['copied']} missing_from_media={vendored['missing']}"
        )
        if vendored["missing"] and snapshot_required:
            self.stdout.write(
                self.style.WARNING(
                    "Some images missing in media/wp (OK if static/frontend/img/site/ is in git)."
                )
            )

        baked = bake_cms_media_urls()
        if any(baked.values()):
            self.stdout.write(
                f"Baked media URLs: pages={baked['pages']} posts={baked['posts']} configs={baked['configs']}"
            )

        call_command("verify_site_media")
        self.stdout.write(self.style.SUCCESS("Deploy site assets OK."))
