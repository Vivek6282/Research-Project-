"""
Trackside Driving Sessions — Corner deltas view (K1).
GET /api/sessions/<id>/corner-deltas/ : time through each corner on each lap and how
far it is from the session's best. Coach/Admin see any session, a Driver only their own.
"""

from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from driving_sessions.access import can_access_session
from driving_sessions.corner_deltas import build_corner_deltas
from driving_sessions.models import Session

ALLOWED_ROLES = ("coach", "admin", "driver")


class SessionCornerDeltasView(APIView):
    """Corner times of one session; a missing session and one the caller may not see look exactly the same (404)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        """Return {session_id, corners: [...]} for the active corners of the session's track."""
        session = Session.objects.select_related("track").filter(pk=pk).first()
        if session is None or request.user.role not in ALLOWED_ROLES or not can_access_session(request.user, session):
            raise Http404()
        zones = list(session.track.zones.filter(is_active=True))
        return Response({"session_id": str(session.id), "corners": build_corner_deltas(session, zones)})
