from django.core.management.base import BaseCommand

from apps.cms.importers.site import import_site


class Command(BaseCommand):
    help = "Import WP pages, blog posts and site config from SQL dump"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sql",
            default="../turtlecruisebyscubacat/dup-installer/dup-database__46e869c-06090919.sql",
            help="Path to WordPress SQL dump",
        )

    def handle(self, *args, **options):
        stats = import_site(options["sql"])
        self.stdout.write(self.style.SUCCESS(f"Imported: {stats}"))
