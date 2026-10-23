"""Trackside — Tracks URL routes."""

from django.urls import path
from tracks.views_corners import TrackCornersView, TrackDuplicateView
from tracks.views_draw import TrackDrawConfirmView, TrackDrawPreviewView
from tracks.views_import import TrackImportConfirmView, TrackImportPreviewView
from tracks.views import (
    TrackListCreateView,
    TrackDetailView,
    ZoneListCreateView,
    ZoneDetailView,
    TrackReferenceLineView,
    DemoCircuitView,
    TrackRestoreView,
    ZoneLimitHistoryView,
)
from tracks.views_survey import TrackSurveyView

urlpatterns = [
    path("import/preview/", TrackImportPreviewView.as_view(), name="track-import-preview"),
    path("import/confirm/", TrackImportConfirmView.as_view(), name="track-import-confirm"),
    path("draw/preview/", TrackDrawPreviewView.as_view(), name="track-draw-preview"),
    path("draw/confirm/", TrackDrawConfirmView.as_view(), name="track-draw-confirm"),
    path("demo-circuit/", DemoCircuitView.as_view(), name="demo-circuit"),
    path("", TrackListCreateView.as_view(), name="track-list-create"),
    path("<uuid:pk>/", TrackDetailView.as_view(), name="track-detail"),
    path("<uuid:pk>/corners/", TrackCornersView.as_view(), name="track-corners"),
    path("<uuid:pk>/duplicate/", TrackDuplicateView.as_view(), name="track-duplicate"),
    path("<uuid:pk>/restore/", TrackRestoreView.as_view(), name="track-restore"),
    path("<uuid:pk>/reference-line/", TrackReferenceLineView.as_view(), name="track-reference-line"),
    path("<uuid:pk>/survey/", TrackSurveyView.as_view(), name="track-survey"),
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
    path(
        "<uuid:track_pk>/zones/<uuid:pk>/limit-history/",
        ZoneLimitHistoryView.as_view(),
        name="zone-limit-history",
    ),
]
