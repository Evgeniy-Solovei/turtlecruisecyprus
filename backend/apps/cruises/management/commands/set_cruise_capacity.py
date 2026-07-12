from django.core.management.base import BaseCommand

from apps.cruises.models import Cruise


class Command(BaseCommand):
    help = "Set default_capacity for all active cruises (useful for staging sold-out tests)."

    def add_arguments(self, parser):
        parser.add_argument("capacity", type=int, help="Seat capacity per cruise, e.g. 3")
        parser.add_argument(
            "--all",
            action="store_true",
            help="Update inactive cruises too.",
        )

    def handle(self, *args, **options):
        capacity = max(int(options["capacity"]), 1)
        qs = Cruise.objects.all() if options["all"] else Cruise.objects.filter(is_active=True)
        updated = qs.update(default_capacity=capacity)
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated default_capacity={capacity} for {updated} cruise(s)."
            )
        )
        for cruise in qs.order_by("code"):
            self.stdout.write(f"  {cruise.code}: {cruise.default_capacity}")
