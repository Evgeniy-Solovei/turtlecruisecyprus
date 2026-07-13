from django.core.management.base import BaseCommand

from apps.cms.site_media import bake_cms_media_urls, vendor_site_media


class Command(BaseCommand):
    help = "Copy all CMS-referenced photos into static/frontend/img/site/ (committed, WhiteNoise)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report only, do not copy files",
        )

    def handle(self, *args, **options):
        stats = vendor_site_media(dry_run=options["dry_run"])
        msg = (
            f"Site media: referenced={stats['referenced']} copied={stats['copied']} "
            f"skipped={stats['skipped']} missing={stats['missing']}"
        )
        if stats["missing"]:
            self.stdout.write(self.style.WARNING(msg))
            self.stdout.write(
                "Missing files: run sync_wp_media or sync_wp_media_live, then re-run vendor_site_media."
            )
        else:
            self.stdout.write(self.style.SUCCESS(msg))
            baked = bake_cms_media_urls()
            if any(baked.values()):
                self.stdout.write(
                    f"Baked CMS media URLs: pages={baked['pages']} posts={baked['posts']} configs={baked['configs']}"
                )
        self.stdout.write("URLs in HTML resolve to /static/frontend/img/site/ on deploy.")
