from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import Booking
from apps.payments.models import Payment


class Command(BaseCommand):
    help = "Fill paid_at / confirmed_at for records imported from WordPress without dates."

    def handle(self, *args, **options):
        payments_updated = 0
        for payment in Payment.objects.filter(status=Payment.Status.SUCCEEDED, paid_at__isnull=True).iterator():
            payment.paid_at = payment.created_at
            payment.save(update_fields=["paid_at", "updated_at"])
            payments_updated += 1

        bookings_updated = 0
        for booking in Booking.objects.filter(status=Booking.Status.CONFIRMED, confirmed_at__isnull=True).iterator():
            booking.confirmed_at = booking.updated_at or booking.created_at or timezone.now()
            booking.save(update_fields=["confirmed_at", "updated_at"])
            bookings_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill done: payments paid_at={payments_updated}, bookings confirmed_at={bookings_updated}"
            )
        )
