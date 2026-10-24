"""Trackside — Academy URL routes."""

from django.urls import path

from academy.views import AcademySettingsView, DriverConsentView

urlpatterns = [
    path("settings/", AcademySettingsView.as_view(), name="academy-settings"),
    path("drivers/<uuid:pk>/consent/", DriverConsentView.as_view(), name="driver-consent"),
]
