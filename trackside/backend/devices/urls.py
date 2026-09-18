"""Trackside — Devices URL routes."""

from django.urls import path
from devices.views import (
    DeviceListCreateView, 
    DeviceDetailView,
    AdminDeviceCommandView,
    DevicePendingCommandsView,
    DeviceCompleteCommandView
)

urlpatterns = [
    path("", DeviceListCreateView.as_view(), name="device-list-create"),
    path("<uuid:pk>/", DeviceDetailView.as_view(), name="device-detail"),
    path("<uuid:pk>/commands/", AdminDeviceCommandView.as_view(), name="device-commands"),
    path("me/commands/pending/", DevicePendingCommandsView.as_view(), name="device-commands-pending"),
    path("me/commands/<uuid:pk>/complete/", DeviceCompleteCommandView.as_view(), name="device-commands-complete"),
]
