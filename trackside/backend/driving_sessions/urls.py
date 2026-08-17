"""Trackside — Sessions URL routes."""

from django.urls import path
from driving_sessions.views import (
    AlertSummaryView,
    RosterStatusView,
    SessionListCreateView,
    SessionDetailView,
    TelemetryListCreateView,
    AlertListView,
    BiometricListCreateView,
    SessionNoteListCreateView,
)

urlpatterns = [
    path("", SessionListCreateView.as_view(), name="session-list-create"),
    path("alerts/summary/", AlertSummaryView.as_view(), name="alert-summary"),
    path("roster-status/", RosterStatusView.as_view(), name="roster-status"),
    path("<uuid:pk>/", SessionDetailView.as_view(), name="session-detail"),
    path(
        "<uuid:session_pk>/telemetry/",
        TelemetryListCreateView.as_view(),
        name="telemetry-list-create",
    ),
    path(
        "<uuid:session_pk>/alerts/",
        AlertListView.as_view(),
        name="alert-list",
    ),
    path(
        "<uuid:session_pk>/biometrics/",
        BiometricListCreateView.as_view(),
        name="biometric-list-create",
    ),
    path(
        "<uuid:session_pk>/notes/",
        SessionNoteListCreateView.as_view(),
        name="note-list-create",
    ),
]


