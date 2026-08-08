"""Trackside — Drivers URL routes."""

from django.urls import path
from drivers.views import ThresholdListCreateView, ThresholdsByDriverView

urlpatterns = [
    path(
        "thresholds/",
        ThresholdListCreateView.as_view(),
        name="threshold-list-create",
    ),
    path(
        "<uuid:driver_pk>/thresholds/",
        ThresholdsByDriverView.as_view(),
        name="driver-thresholds",
    ),
]
