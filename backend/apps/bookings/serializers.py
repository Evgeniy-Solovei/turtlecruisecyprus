from __future__ import annotations

from datetime import date

from rest_framework import serializers

from apps.cruises.time_utils import format_time_range

from .models import Booking
from .services import BookingHoldInput


class BookingHoldSerializer(serializers.Serializer):
    cruise_type = serializers.CharField(required=False)
    cruise_code = serializers.CharField(required=False)
    cruise_date = serializers.DateField()
    adults = serializers.IntegerField(required=False, min_value=1)
    adults_count = serializers.IntegerField(required=False, min_value=1)
    children = serializers.IntegerField(required=False, min_value=0)
    children_count = serializers.IntegerField(required=False, min_value=0)
    first_name = serializers.CharField()
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField()
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    session_id = serializers.CharField(required=False, allow_blank=True)
    tc_session_id = serializers.CharField(required=False, allow_blank=True)

    def to_input(self) -> BookingHoldInput:
        data = self.validated_data
        return BookingHoldInput(
            cruise_code=data.get("cruise_code") or data.get("cruise_type"),
            cruise_date=data["cruise_date"],
            adults_count=data.get("adults_count") or data.get("adults") or 1,
            children_count=data.get("children_count") if data.get("children_count") is not None else data.get("children", 0),
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
            email=data["email"],
            phone=data["phone"],
            customer_notes=data.get("customer_notes", ""),
            source=data.get("source", "web"),
            session_id=data.get("session_id") or data.get("tc_session_id") or "",
        )


class BookingSerializer(serializers.ModelSerializer):
    cruise = serializers.CharField(source="cruise.code")
    customer_name = serializers.CharField(source="customer.full_name")
    email = serializers.EmailField(source="customer.email")
    phone = serializers.CharField(source="customer.phone")
    cruise_time = serializers.SerializerMethodField()
    checkout_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "public_id",
            "status",
            "cruise",
            "cruise_date",
            "start_time",
            "end_time",
            "cruise_time",
            "adults_count",
            "children_count",
            "total_seats",
            "adult_unit_price",
            "child_unit_price",
            "total_amount",
            "currency",
            "checkout_expires_at",
            "cancel_reason",
            "customer_name",
            "email",
            "phone",
        ]

    def get_checkout_expires_at(self, obj: Booking) -> str | None:
        if obj.status != Booking.Status.PENDING_PAYMENT:
            return None
        from apps.payments.models import Payment
        from apps.payments.services import checkout_deadline_for_payment

        payment = Payment.objects.filter(booking=obj).order_by("-created_at").first()
        if not payment:
            return None
        return checkout_deadline_for_payment(payment).isoformat()

    def get_cruise_time(self, obj: Booking) -> str:
        return format_time_range(obj.start_time, obj.end_time)
