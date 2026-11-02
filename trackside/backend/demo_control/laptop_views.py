"""
Trackside — Laptop link API (Coach and Admin).

POST /api/laptop-link/start/   body {driver_id, track_id}  -> session, one-time token, zones, backend URL
POST /api/laptop-link/stop/                      -> ends the link (closes the session, drops the token)
GET  /api/laptop-link/status/                    -> idle | waiting | receiving | quiet
Works on a hosted (production) server: it never runs the simulator, it only prepares a session.
"""

from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLogEntry
from accounts.permissions import IsAdminOrCoach
from demo_control.demo_run import DemoRunError, parse_uuid
from demo_control.laptop_link import end_link, link_status, start_link
from tracks.models import Track

User = get_user_model()


class LaptopLinkBase(APIView):
    """Session-authenticated, Coach or Admin only."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminOrCoach]


def audit(request, action: str, details: str) -> None:
    """Write one audit entry for the link."""
    AuditLogEntry.objects.create(actor=request.user, action=action, details=details)


class LaptopLinkStartView(LaptopLinkBase):
    """Start a link for one driver and return what the laptop needs (the token is shown only here)."""

    def post(self, request):
        """Validate the driver and map, create the session and token."""
        try:
            driver = User.objects.filter(pk=parse_uuid(request.data.get("driver_id"), "driver_id")).first()
            track = Track.objects.filter(pk=parse_uuid(request.data.get("track_id"), "track_id")).first()
            if track is None:
                raise DemoRunError("That map does not exist.")
            result = start_link(request, driver, track)
        except DemoRunError as error:
            return Response({"detail": error.message}, status=error.status_code)
        audit(request, AuditLogEntry.Action.SIMULATOR_START, f"Laptop link started for {result['driver_name']} on {result['track_name']}")
        return Response(result)


class LaptopLinkStopView(LaptopLinkBase):
    """End the link (safe to press twice)."""

    def post(self, request):
        """Close the session and drop the token."""
        try:
            end_link(request)
        except DemoRunError as error:
            return Response({"detail": error.message}, status=error.status_code)
        audit(request, AuditLogEntry.Action.SIMULATOR_STOP, "Laptop link ended")
        return Response({"state": "idle"})


class LaptopLinkStatusView(LaptopLinkBase):
    """Where the link is right now."""

    def get(self, request):
        """Idle, waiting, receiving or quiet."""
        try:
            return Response(link_status(request))
        except DemoRunError as error:
            return Response({"detail": error.message}, status=error.status_code)
