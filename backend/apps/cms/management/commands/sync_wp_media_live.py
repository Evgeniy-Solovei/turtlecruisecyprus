from __future__ import annotations

import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.cms.importers.live import PROD_BASE, extract_media_relpaths_from_html
from apps.cms.models import SitePage


class Command(BaseCommand):
    help = "Download missing /media/wp files referenced in imported CMS HTML from prod."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max files to download (0 = all missing)",
        )

    def handle(self, *args, **options):
        rel_paths: set[str] = set()
        for page in SitePage.objects.all():
            rel_paths |= extract_media_relpaths_from_html(page.body_html)

        target = Path(settings.MEDIA_ROOT) / "wp"
        target.mkdir(parents=True, exist_ok=True)

        missing = sorted(
            rel for rel in rel_paths if rel and not (target / rel).is_file()
        )
        if options["limit"]:
            missing = missing[: options["limit"]]

        downloaded = 0
        failed = 0
        for rel in missing:
            url = f"{PROD_BASE}/wp-content/uploads/{rel}"
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    ["curl", "-fsSL", "-o", str(dest), url],
                    check=True,
                    timeout=120,
                )
                downloaded += 1
                if downloaded % 25 == 0:
                    self.stdout.write(f"Downloaded {downloaded}/{len(missing)}...")
            except (subprocess.CalledProcessError, OSError) as exc:
                failed += 1
                self.stdout.write(self.style.WARNING(f"Failed {rel}: {exc}"))

        total = sum(1 for _ in target.rglob("*") if _.is_file())
        self.stdout.write(
            self.style.SUCCESS(
                f"Media sync: needed={len(missing)} downloaded={downloaded} failed={failed} total_files={total}"
            )
        )
