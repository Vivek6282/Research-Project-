"""Trackside — Preferences URL routes."""

from django.urls import path
from preferences.views import MyPreferencesView

urlpatterns = [
    path("me/", MyPreferencesView.as_view(), name="my-preferences"),
]
