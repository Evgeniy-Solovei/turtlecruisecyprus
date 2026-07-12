from django.conf import settings
from django.core.management.base import BaseCommand

from apps.migration_wp.importers.motopress import import_dump


class Command(BaseCommand):
    help = "Import WordPress/MotoPress data from the SQL dump."

    def add_arguments(self, parser):
        parser.add_argument("--sql", default=settings.WP_SQL_DUMP_PATH)

    def handle(self, *args, **options):
        stats = import_dump(options["sql"])
        self.stdout.write(self.style.SUCCESS(f"Import finished: {stats}"))
