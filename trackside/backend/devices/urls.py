"""Trackside — Devices URL routes."""

from django.urls import path
from devices.views import DeviceListCreateView, DeviceDetailView

urlpatterns = [
    path("", DeviceListCreateView.as_view(), name="device-list-create"),
    path("<uuid:pk>/", DeviceDetailView.as_view(), name="device-detail"),
]
