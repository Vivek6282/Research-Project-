"""Trackside — Tracks URL routes."""

from django.urls import path
from tracks.views import (
    TrackListCreateView,
    TrackDetailView,
    ZoneListCreateView,
    ZoneDetailView,
)

urlpatterns = [
    path("", TrackListCreateView.as_view(), name="track-list-create"),
    path("<uuid:pk>/", TrackDetailView.as_view(), name="track-detail"),
    path(
        "<uuid:track_pk>/zones/",
        ZoneListCreateView.as_view(),
        name="zone-list-create",
    ),
    path(
        "<uuid:track_pk>/zones/<uuid:pk>/",
        ZoneDetailView.as_view(),
        name="zone-detail",
    ),
]
