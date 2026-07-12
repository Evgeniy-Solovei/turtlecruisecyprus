from django.urls import path

from . import views

urlpatterns = [
    path("stripe/payment-intent/", views.stripe_payment_intent, name="stripe-payment-intent"),
    path("stripe/confirm/", views.stripe_confirm, name="stripe-confirm"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe-webhook"),
]
