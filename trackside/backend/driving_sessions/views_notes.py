"""
Trackside Driving Sessions — Coaching Notes Views.
This module provides endpoints for viewing and recording coach notes and feedback
tied to driving sessions and specific track zones.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, exceptions
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsCoach
from driving_sessions.access import sessions_visible_to, can_access_session
from driving_sessions.models import Session, SessionNote
from driving_sessions.serializers import SessionNoteSerializer


class SessionNoteListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/<uuid>/notes/ — list coaching notes for an authorized session.
    POST /api/sessions/<uuid>/notes/ — create coaching debrief note (Coach only).

    Security:
    - POST is strictly restricted to Coach users via IsCoach.
    - Queryset is scoped to sessions visible to the user.
    """

    serializer_class = SessionNoteSerializer

    def get_permissions(self):
        """
        Enforces IsCoach on note creation and IsAuthenticated on note listing.
        Input: None.
        Output: List of permission instances.
        """
        if self.request.method == "POST":
            return [IsCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Retrieves session notes scoped to sessions the user is authorized to view.
        Input: None.
        Output: SessionNote QuerySet with coach and zone pre-fetched.
        """
        session_id = self.kwargs.get("session_pk")
        visible_sessions = sessions_visible_to(self.request.user)
        return SessionNote.objects.filter(
            session_id=session_id,
            session__in=visible_sessions,
        ).select_related("coach", "zone")

    def perform_create(self, serializer):
        """
        Saves the note with coach bound to request.user and session bound to the target session.
        Input: Validated SessionNote serializer.
        Output: None.
        """
        session_id = self.kwargs.get("session_pk")
        target_session = get_object_or_404(Session, pk=session_id)
        if not can_access_session(self.request.user, target_session):
            raise exceptions.PermissionDenied("You are not authorized for this session.")
        serializer.save(
            coach=self.request.user,
            session=target_session,
        )
