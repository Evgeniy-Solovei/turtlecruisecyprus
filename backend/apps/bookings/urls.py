from django.urls import path

from . import views

urlpatterns = [
    path("hold/", views.create_hold, name="booking-hold"),
    path("<str:public_id>/trace/", views.booking_trace, name="booking-trace"),
    path("<str:public_id>/status/", views.booking_status, name="booking-status"),
    path("<str:public_id>/cancel/", views.cancel, name="booking-cancel"),
    path("<str:public_id>/", views.booking_detail, name="booking-detail"),
]
