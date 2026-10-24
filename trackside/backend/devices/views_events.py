"""
Trackside — POST /api/devices/events/ (Phase 2.0).

Senders: a device with its own token, or a signed-in Driver (the phone page) for
their own active session, with consent recorded. Coaches and admins cannot send.
A repeated event_id from the same sender returns the stored event (200), so a
device can retry safely; the same id from a different sender is refused (409).
"""

from django.db import IntegrityError, transaction
from rest_framework import exceptions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from academy.consent import require_consent
from devices.authentication import DeviceTokenAuthentication
from devices.event_models import DeviceEvent
from devices.event_serializers import DeviceEventSerializer
from driving_sessions.access import sessions_visible_to

class SessionEnded(exceptions.APIException):
    """409: the session has already ended, so it takes no new events."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "This session has ended."


DRIVER_EVENT_TYPES = {"crash_suspected", "lost_contact", "driver_ok", "heartbeat"}
SESSION_REQUIRED = {"crash_suspected", "lost_contact", "driver_ok"}


class DeviceEventView(GenericAPIView):
    """Store one event from a device or a driver's phone page."""

    authentication_classes = [SessionAuthentication, DeviceTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceEventSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "device_events"

    def sender(self, request):
        """(device, user) of the sender; refuses (403) anyone who is not a device or a consenting driver."""
        role = getattr(request.user, "role", None)
        if role == "device":
            return request.user.device, None
        if role == "driver":
            require_consent(request.user)
            return None, request.user
        raise exceptions.PermissionDenied("Only devices and drivers can send device events.")

    def post(self, request):
        """Check the sender, answer repeats, then validate and store the event."""
        device, user = self.sender(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        stored = DeviceEvent.objects.filter(event_id=data["event_id"]).first()
        if stored is not None:
            return self.repeat_response(stored, device, user)
        if user is not None and data["event_type"] not in DRIVER_EVENT_TYPES:
            raise exceptions.PermissionDenied("A driver's phone cannot send this event type.")
        session = self.checked_session(request, data)
        self.check_driver_ok(data, session)
        try:
            with transaction.atomic():
                event = serializer.save(device=device, sent_by=user, session=session)
        except IntegrityError:   # the same event arrived twice at the same moment
            return self.repeat_response(DeviceEvent.objects.get(event_id=data["event_id"]), device, user)
        return Response(self.get_serializer(event).data, status=status.HTTP_201_CREATED)

    def repeat_response(self, stored, device, user):
        """The stored event for a retry by the same sender (200); a clash with someone else's id is refused."""
        if not stored.sender_matches(device, user):
            return Response({"detail": "This event_id is already used."}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(stored).data, status=status.HTTP_200_OK)

    def checked_session(self, request, data):
        """The session the event belongs to: visible to the sender (else 404) and still running (else 409)."""
        session_id = data.pop("session_id", None)
        if session_id is None:
            if data["event_type"] in SESSION_REQUIRED:
                raise exceptions.ValidationError({"session": "is required for this event type"})
            return None
        session = sessions_visible_to(request.user).filter(pk=session_id).first()
        if session is None:
            raise exceptions.NotFound("Session not found.")
        if session.ended_at is not None:
            raise SessionEnded()
        return session

    def check_driver_ok(self, data, session):
        """A "driver OK" event must point at a crash event of the same session."""
        if data["event_type"] != "driver_ok":
            return
        crash_id = data["payload"]["crash_event_id"]
        if not DeviceEvent.objects.filter(event_id=crash_id, session=session, event_type="crash_suspected").exists():
            raise exceptions.ValidationError({"payload": {"crash_event_id": "no crash event with this id in this session"}})
