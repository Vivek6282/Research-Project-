"""
Trackside — The phone's calibration and warnings for one session (Phase 2.1).

GET  /api/sessions/<id>/phone-calibration/   the stored mounting and warnings (anyone who may see the session)
PUT  /api/sessions/<id>/phone-calibration/   the driver's phone saves its mounting and raises warnings
"""

import math

from django.shortcuts import get_object_or_404
from rest_framework import exceptions, serializers
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from driving_sessions.access import sessions_visible_to
from driving_sessions.models import Session
from driving_sessions.phone_rules import check_phone_may_send

ALLOWED_FLAGS = ("sensor_disagreement", "mount_moved")


def check_direction(value):
    """Three finite numbers forming a direction of sensible size (it is scaled to length 1 before saving)."""
    if (not isinstance(value, list) or len(value) != 3
            or not all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) for n in value)):
        raise serializers.ValidationError("must be a list of three numbers")
    length = math.sqrt(sum(n * n for n in value))
    if not 0.1 <= length <= 30.0:
        raise serializers.ValidationError("is too short or too long to be a direction")
    return [round(n / length, 5) for n in value]


class PhoneCalibrationSerializer(serializers.Serializer):
    """Gravity and forward directions in the phone's own axes, plus any warnings; all optional."""

    gravity = serializers.JSONField(required=False)
    forward = serializers.JSONField(required=False)
    flags = serializers.ListField(child=serializers.ChoiceField(choices=ALLOWED_FLAGS), required=False, max_length=10)

    def validate_gravity(self, value):
        """Gravity: a direction."""
        return check_direction(value)

    def validate_forward(self, value):
        """Forward: a direction."""
        return check_direction(value)

    def validate(self, attrs):
        """Forward must be close to level: at most 30 degrees from perpendicular to gravity."""
        gravity, forward = attrs.get("gravity"), attrs.get("forward")
        if gravity and forward and abs(sum(g * f for g, f in zip(gravity, forward))) > 0.5:
            raise serializers.ValidationError({"forward": "is not level; drive straight on flat ground and try again"})
        return attrs


class PhoneCalibrationView(GenericAPIView):
    """Read or save one session's phone mounting and warnings."""

    serializer_class = PhoneCalibrationSerializer

    def get_session(self, pk) -> Session:
        """The session if the caller may see it (404 otherwise, same as missing)."""
        return get_object_or_404(sessions_visible_to(self.request.user), pk=pk)

    def payload(self, session: Session) -> dict:
        """What both GET and PUT answer."""
        return {"session": str(session.id), "data_source": session.data_source,
                "phone_calibration": session.phone_calibration, "sensor_flags": session.sensor_flags}

    def get(self, request, pk=None):
        """The stored calibration and warnings."""
        return Response(self.payload(self.get_session(pk)))

    def put(self, request, pk=None):
        """Only the session's own driver, with consent, on a running real-time session."""
        session = self.get_session(pk)
        if getattr(request.user, "role", None) != "driver":
            raise exceptions.PermissionDenied("Only the driver's phone saves its calibration.")
        if session.ended_at is not None:
            return Response({"detail": "This session has ended."}, status=409)
        check_phone_may_send(request.user, session)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        calibration = dict(session.phone_calibration or {})
        calibration.update({key: data[key] for key in ("gravity", "forward") if key in data})
        flags = list(session.sensor_flags or [])
        for flag in data.get("flags", []):
            if flag not in flags:
                flags.append(flag)
        Session.objects.filter(pk=session.pk).update(phone_calibration=calibration or None, sensor_flags=flags)
        session.refresh_from_db()
        return Response(self.payload(session))
