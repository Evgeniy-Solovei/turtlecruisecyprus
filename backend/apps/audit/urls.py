from django.urls import path

from . import views

urlpatterns = [
    path("events/", views.track_event, name="audit-track-event"),
    path("events/batch/", views.track_events_batch, name="audit-track-events-batch"),
    path("funnel/", views.funnel_summary, name="audit-funnel-summary"),
    path("sessions/<str:session_id>/", views.session_detail, name="audit-session-detail"),
]
