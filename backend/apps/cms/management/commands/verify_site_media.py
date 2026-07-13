from django.core.management.base import BaseCommand, CommandError

from apps.cms.site_media import SITE_MEDIA_STATIC_ROOT, collect_vendored_wp_paths


class Command(BaseCommand):
    help = "Fail deploy if vendored site images or CMS snapshot are incomplete."

    def handle(self, *args, **options):
        from pathlib import Path

        from django.conf import settings

        from apps.cms.models import SitePage

        home = SitePage.objects.filter(slug="", locale="en").first()
        home_len = len((home.body_html or "") if home else "")
        media_wp_left = (home.body_html or "").count("/media/wp/") if home else 0

        referenced = collect_vendored_wp_paths()
        missing = [
            rel
            for rel in sorted(referenced)
            if not (SITE_MEDIA_STATIC_ROOT / rel).is_file()
        ]

        snapshot = Path(settings.BASE_DIR) / "cms_snapshot" / "snapshot.json"
        problems: list[str] = []

        if home_len < 2000:
            problems.append(f"Home CMS body too short ({home_len} chars). Run import_cms_snapshot.")
        if media_wp_left:
            problems.append(f"Home still has {media_wp_left} /media/wp/ URLs. Run bake_cms_media_urls.")
        if missing:
            problems.append(f"{len(missing)} vendored images missing under static/frontend/img/site/")
            for rel in missing[:10]:
                problems.append(f"  - {rel}")
        if not snapshot.is_file():
            problems.append("cms_snapshot/snapshot.json missing — export and commit it.")

        if problems:
            for line in problems:
                self.stdout.write(self.style.ERROR(line))
            raise CommandError("Site media parity check failed.")

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: home={home_len} chars, images={len(referenced)}, snapshot present"
            )
        )
