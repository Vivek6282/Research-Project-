"""
Trackside Driving Sessions — Safety Alert Views.
This module provides endpoints for querying safety and threshold exceedance alerts
associated with active or historical driving sessions.
"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from driving_sessions.access import sessions_visible_to
from driving_sessions.models import Alert
from driving_sessions.serializers import AlertSerializer


class AlertListView(generics.ListAPIView):
    """
    GET /api/sessions/<uuid>/alerts/ — list alerts for an authorized session.

    Security:
    - Scoped via sessions_visible_to helper so drivers cannot view alerts for other drivers.
    """

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retrieves alerts filtered by session UUID and authorized user session visibility.
        Input: None (uses request.user and session_pk kwarg).
        Output: Alert QuerySet with zone pre-fetched.
        """
        session_id = self.kwargs.get("session_pk")
        visible_sessions = sessions_visible_to(self.request.user)
        return Alert.objects.filter(
            session_id=session_id,
            session__in=visible_sessions,
        ).select_related("zone")
