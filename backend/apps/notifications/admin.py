from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import EmailLog, SmsLog, TelegramLog


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ["booking", "recipient", "template_code", "status", "provider_message_id", "sent_at"]
    list_filter = ["provider", "template_code", "status"]
    search_fields = ["booking__public_id", "recipient", "provider_message_id"]
    readonly_fields = ["created_at", "sent_at"]
    fieldsets = (
        ("Письмо", {"fields": ("booking", "provider", "template_code", "recipient", "subject", "status")}),
        ("Провайдер", {"fields": ("provider_message_id", "error")}),
        ("Payload", {"fields": ("payload_snapshot",), "classes": ("collapse",)}),
        ("Даты", {"fields": ("created_at", "sent_at"), "classes": ("collapse",)}),
    )


@admin.register(TelegramLog)
class TelegramLogAdmin(ModelAdmin):
    list_display = ["booking", "recipient", "status", "provider_message_id", "sent_at"]
    list_filter = ["provider", "status"]
    search_fields = ["booking__public_id", "recipient", "provider_message_id"]
    readonly_fields = ["created_at", "sent_at"]

    def has_module_permission(self, request):
        return False


@admin.register(SmsLog)
class SmsLogAdmin(ModelAdmin):
    list_display = ["booking", "recipient", "status", "provider_message_id", "sent_at"]
    list_filter = ["provider", "status"]
    search_fields = ["booking__public_id", "recipient", "provider_message_id"]
    readonly_fields = ["created_at", "sent_at"]
    fieldsets = (
        ("SMS", {"fields": ("booking", "provider", "recipient", "message", "status")}),
        ("Провайдер", {"fields": ("provider_message_id", "error")}),
        ("Даты", {"fields": ("created_at", "sent_at"), "classes": ("collapse",)}),
    )
