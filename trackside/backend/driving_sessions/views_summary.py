"""
Trackside Driving Sessions — Alert Summary and Roster Status Views.
This module provides aggregate reporting endpoints:
- AlertSummaryView: Driver-specific alert distribution across recent sessions and goals.
- RosterStatusView: Live telemetry trajectory monitoring across active drivers.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from driving_sessions.access import sessions_visible_to
from driving_sessions.live_state import is_live_now
from driving_sessions.models import Alert, Telemetry
from driving_sessions.serializers import SessionSerializer
from tracks.models import Zone

User = get_user_model()


class AlertSummaryView(APIView):
    """
    GET /api/sessions/alerts/summary/

    Returns the requesting driver's zone-by-zone alert count breakdown
    across their last 5 sessions, plus latest session goal and best lap.
    Enforces strict user ownership scoping (sessions_visible_to).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Aggregates alert history across the 5 most recent sessions for the target driver.
        Input: Authenticated HTTP GET request, optional ?driver=<uuid> query param for coach/admin.
        Output: JSON summary with zone alert counts, risk statuses, and latest session goal.
        """
        requesting_user = request.user
        visible_sessions = sessions_visible_to(requesting_user)

        driver_param = request.query_params.get("driver") or request.query_params.get("driver_id")
        if driver_param and requesting_user.role in ("coach", "admin"):
            target_driver = get_object_or_404(User, pk=driver_param)
            recent_sessions = list(
                visible_sessions.filter(driver=target_driver)
                .select_related("track")
                .order_by("-started_at")[:5]
            )
        else:
            recent_sessions = list(
                visible_sessions
                .select_related("track")
                .order_by("-started_at")[:5]
            )

        if not recent_sessions:
            return Response(
                {
                    "has_sessions": False,
                    "total_sessions": 0,
                    "zones": [],
                    "latest_session": None,
                },
                status=status.HTTP_200_OK,
            )

        session_ids = [session.id for session in recent_sessions]
        track_ids = list(set(session.track_id for session in recent_sessions if session.track_id))

        track_zones = list(Zone.objects.filter(track_id__in=track_ids).order_by("label"))
        if not track_zones:
            track_zones = list(Zone.objects.all().order_by("label"))

        most_recent_session = recent_sessions[0]
        zone_summaries = self.zone_summaries(track_zones, session_ids, most_recent_session.track_id)


        has_goal = bool(most_recent_session.goal_text and most_recent_session.goal_text.strip())
        session_facts = SessionSerializer(most_recent_session).data
        newest_reading_at = (
            Telemetry.objects.filter(session=most_recent_session)
            .order_by("-recorded_at").values_list("recorded_at", flat=True).first()
        )
        latest_session_details = {
            "id": str(most_recent_session.id),
            "mode": most_recent_session.mode,
            "goal_text": most_recent_session.goal_text if has_goal else "",
            "goal_passed": most_recent_session.goal_passed if has_goal else None,
            "started_at": most_recent_session.started_at,
            "track_name": most_recent_session.track.name if most_recent_session.track else "Standard Track",
            "best_lap_time": session_facts.get("best_lap"),
            "is_demo": most_recent_session.is_demo,
            # What the coach sees about the same run, so both screens agree
            "ended_at": most_recent_session.ended_at,
            "live": is_live_now(most_recent_session, newest_reading_at),
            "laps": session_facts.get("laps"),
            "alert_count": session_facts.get("alert_count"),
            "duration": session_facts.get("duration"),
            "max_g": session_facts.get("max_g"),
        }

        return Response(
            {
                "has_sessions": True,
                "total_sessions": len(recent_sessions),
                "zones": zone_summaries,
                "latest_session": latest_session_details,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def zone_summaries(track_zones, session_ids, latest_track_id):
        """One tile per corner name: alerts of the last sessions added up, the limit of the latest track."""
        merged = {}
        for zone in track_zones:
            tile = merged.setdefault(zone.label, {"count": 0, "red_count": 0, "zone": zone})
            tile["count"] += Alert.objects.filter(session_id__in=session_ids, zone=zone).count()
            tile["red_count"] += Alert.objects.filter(
                session_id__in=session_ids, zone=zone, severity=Alert.Severity.RED).count()
            if zone.track_id == latest_track_id:
                tile["zone"] = zone
        summaries = []
        for label, tile in merged.items():
            if tile["count"] == 0:
                zone_status, status_color = "Clean", "#33D17E"
            elif tile["red_count"] > 0 or tile["count"] >= 5:
                zone_status, status_color = "High Risk", "#E5473C"
            else:
                zone_status, status_color = "Caution", "#F2A93B"
            summaries.append({
                "name": label, "count": tile["count"], "red_count": tile["red_count"],
                "status": zone_status, "color": status_color, "threshold": tile["zone"].threshold_g,
            })
        return summaries


class RosterStatusView(APIView):
    """
    GET /api/sessions/roster-status/

    Returns live and recent trajectory status for drivers visible to coach/admin.
    Shows current lateral-g, active zone threshold, trajectory stage, and pit status.
    """

    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        # Maps NotAuthenticated exception to 401 response for unauthenticated clients.
        from rest_framework.exceptions import NotAuthenticated
        if isinstance(exc, NotAuthenticated):
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

    def get(self, request):
        """
        Compiles the active roster status for all drivers visible to the requester.
        Input: Authenticated HTTP GET request.
        Output: JSON containing roster array with driver metrics and intervention stages.
        """
        requesting_user = request.user
        visible_sessions = sessions_visible_to(requesting_user)

        if requesting_user.role == "driver":
            authorized_drivers = [requesting_user]
        elif requesting_user.role == "device":
            if getattr(requesting_user, "assigned_to", None):
                authorized_drivers = [requesting_user.assigned_to]
            else:
                authorized_drivers = []
        elif requesting_user.role in ("coach", "admin"):
            authorized_drivers = list(User.objects.filter(role="driver").order_by("name"))
        else:
            authorized_drivers = []

        roster_entries = []
        for driver in authorized_drivers:
            latest_session = visible_sessions.filter(driver=driver).order_by("-started_at").first()

            if not latest_session:
                session_state = "none"
            elif latest_session.ended_at is not None:
                session_state = "ended"
            else:
                session_state = "in_progress"

            latest_telemetry = None
            if latest_session:
                latest_telemetry = Telemetry.objects.filter(session=latest_session).order_by("-recorded_at").first()

            if latest_telemetry:
                measured_current_g = round(latest_telemetry.lateral_g, 2) if latest_telemetry.lateral_g is not None else None
                active_zone_name = latest_telemetry.zone.label if (latest_telemetry.zone and latest_telemetry.zone.label) else None
                effective_threshold_g = round(latest_telemetry.zone.threshold_g, 2) if (latest_telemetry.zone and latest_telemetry.zone.threshold_g is not None) else None

                if measured_current_g is not None and effective_threshold_g is not None:
                    if measured_current_g >= effective_threshold_g:
                        trajectory_stage = "intervene"
                    elif measured_current_g >= effective_threshold_g * 0.82:
                        trajectory_stage = "monitoring"
                    else:
                        trajectory_stage = "nominal"
                else:
                    trajectory_stage = "nominal"

                is_live = is_live_now(latest_session, latest_telemetry.recorded_at)
            else:
                measured_current_g = None
                active_zone_name = None
                effective_threshold_g = None
                trajectory_stage = "no_data"
                is_live = False

            roster_entries.append(
                {
                    "driver_id": str(driver.id),
                    "driver_name": driver.name,
                    "driver_code": driver.driver_code,
                    "is_active": driver.is_active,
                    "current_g": measured_current_g,
                    "active_zone": active_zone_name,
                    "active_threshold": effective_threshold_g,
                    "stage": trajectory_stage,
                    "session_state": session_state,
                    "live": is_live,
                }
            )

        return Response({"roster": roster_entries}, status=status.HTTP_200_OK)
