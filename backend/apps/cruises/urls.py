from django.urls import path

from . import views

urlpatterns = [
    path("", views.cruise_list, name="cruise-list"),
    path("<slug:code>/availability/", views.cruise_availability, name="cruise-availability"),
]
