from pathlib import Path

from django.core.management.base import BaseCommand

from apps.cms.snapshot import SNAPSHOT_PATH, export_cms_snapshot


class Command(BaseCommand):
    help = "Export SitePage/SiteConfig/BlogPost into cms_snapshot/snapshot.json (commit to git for deploy)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help=f"Output path (default: {SNAPSHOT_PATH})",
        )

    def handle(self, *args, **options):
        path = Path(options["output"]) if options["output"] else None
        stats = export_cms_snapshot(path)
        self.stdout.write(
            self.style.SUCCESS(
                f"Exported pages={stats['pages']} configs={stats['configs']} "
                f"posts={stats['posts']} -> {stats['path']}"
            )
        )
        self.stdout.write("Commit cms_snapshot/snapshot.json + static/frontend/img/site/ together.")
