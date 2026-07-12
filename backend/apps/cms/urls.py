from django.urls import path

from . import views

urlpatterns = [
    path("load-more/", views.BlogLoadMoreView.as_view(), name="blog-load-more"),
    path("<slug:slug>/", views.BlogPostDetailView.as_view(), name="blog-detail"),
]
