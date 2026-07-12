from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Payment, WebhookLog


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = [
        "booking_public_id",
        "customer_info",
        "cruise_info",
        "amount",
        "status",
        "paid_at",
    ]
    list_filter = ["status", "provider"]
    search_fields = [
        "booking__public_id",
        "booking__customer__email",
        "booking__customer__first_name",
        "booking__customer__last_name",
        "stripe_checkout_session_id",
        "stripe_payment_intent_id",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "paid_at",
        "stripe_help",
    ]
    fieldsets = (
        (
            "Кому принадлежит",
            {
                "description": "Всегда смотрите сюда. Номер брони = тот же, что в разделе «Брони».",
                "fields": ("booking", "stripe_help"),
            },
        ),
        ("Сумма и статус", {"fields": ("amount", "currency", "status", "paid_at", "provider")}),
        (
            "Stripe (техническое)",
            {
                "description": "PaymentIntent появляется после успешной оплаты. До оплаты заполнен только Checkout Session.",
                "fields": (
                    "stripe_checkout_session_id",
                    "stripe_payment_intent_id",
                    "stripe_charge_id",
                    "raw_provider_status",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Служебное", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="№ брони", ordering="booking__public_id")
    def booking_public_id(self, obj: Payment) -> str:
        return obj.booking.public_id

    @admin.display(description="Клиент", ordering="booking__customer__email")
    def customer_info(self, obj: Payment) -> str:
        c = obj.booking.customer
        return f"{c.full_name} · {c.email}"

    @admin.display(description="Круиз", ordering="booking__cruise_date")
    def cruise_info(self, obj: Payment) -> str:
        b = obj.booking
        return f"{b.cruise.name} · {b.cruise_date}"

    @admin.display(description="Подсказка")
    def stripe_help(self, obj: Payment) -> str:
        if obj.status == Payment.Status.SUCCEEDED and obj.paid_at:
            return "Оплата прошла. PaymentIntent и дата «Оплачено» должны быть заполнены."
        if obj.stripe_checkout_session_id and not obj.stripe_payment_intent_id:
            return "Клиент ещё не оплатил или оплата в процессе. Это нормально — ID появится после успешной оплаты."
        return "Платёж создан, ждём действия клиента в Stripe."

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("booking__customer", "booking__cruise")


@admin.register(WebhookLog)
class WebhookLogAdmin(ModelAdmin):
    list_display = ["provider", "event_type", "event_id", "signature_valid", "processed", "received_at"]
    list_filter = ["provider", "event_type", "signature_valid", "processed"]
    search_fields = ["event_id", "event_type"]
    readonly_fields = ["received_at", "processed_at"]
    fieldsets = (
        ("Webhook", {"fields": ("provider", "event_id", "event_type", "signature_valid", "processed")}),
        ("Обработка", {"fields": ("processing_error", "received_at", "processed_at")}),
        ("Payload", {"fields": ("payload",), "classes": ("collapse",)}),
    )

    def has_module_permission(self, request):
        return True
