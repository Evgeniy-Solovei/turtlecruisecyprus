from django.core.management.base import BaseCommand

from apps.cms.importers.live import import_live_pages, import_live_site_config


class Command(BaseCommand):
    help = "Import published page HTML from live turtlecruisecyprus.com (WP REST API)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-body",
            type=int,
            default=500,
            help="Skip pages with rendered HTML shorter than this (chars)",
        )

    def handle(self, *args, **options):
        stats = import_live_pages(min_body=options["min_body"])
        cfg = import_live_site_config()
        self.stdout.write(
            self.style.SUCCESS(
                f"Live import: fetched={stats['fetched']} imported={stats['imported']} "
                f"skipped={stats['skipped']} footer={cfg['footer']} socials={cfg['socials']}"
            )
        )
        self.stdout.write("Run: python manage.py sync_wp_media_live")
