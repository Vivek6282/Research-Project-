"""Trackside — Laptop link URL routes (mounted at /api/laptop-link/)."""

from django.urls import path

from demo_control.laptop_views import LaptopLinkStartView, LaptopLinkStatusView, LaptopLinkStopView

urlpatterns = [
    path("start/", LaptopLinkStartView.as_view(), name="laptop-link-start"),
    path("stop/", LaptopLinkStopView.as_view(), name="laptop-link-stop"),
    path("status/", LaptopLinkStatusView.as_view(), name="laptop-link-status"),
]
