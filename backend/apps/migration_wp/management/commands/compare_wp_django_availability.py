from datetime import date

from django.core.management.base import BaseCommand

from apps.bookings.selectors import booked_seats_for_date
from apps.cruises.models import Cruise
from apps.cruises.services import effective_capacity


class Command(BaseCommand):
    help = "Print Django availability for manual comparison with WordPress/MotoPress."

    def add_arguments(self, parser):
        parser.add_argument("--date", required=True)

    def handle(self, *args, **options):
        cruise_date = date.fromisoformat(options["date"])
        for cruise in Cruise.objects.filter(is_active=True):
            capacity = effective_capacity(cruise, cruise_date)
            booked = booked_seats_for_date(cruise, cruise_date)
            self.stdout.write(f"{cruise.code}: capacity={capacity} booked={booked} available={max(capacity - booked, 0)}")
