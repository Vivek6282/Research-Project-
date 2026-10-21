"""
Trackside — Demo Control API Views.

Endpoints:
- POST /api/demo/simulator/start/   body: {track_id, driver_id, laps 1-20, pace safe|edge|over}
- POST /api/demo/simulator/stop/
- GET  /api/demo/simulator/status/

Enforces security rules:
1. 404 when DEMO_TOOLS_ENABLED is not 'true'.
2. 403 when DJANGO_ENV is 'production'.
3. 403 for non-coach roles, 401 for unauthenticated.
4. Fixed command execution (no shell); laps must be an integer 1..20, pace one of three words.
5. 409 if already running, stop is idempotent.
6. Writes AuditLogEntry on start and on stop.
Secrets (the device token) go to the child process only through its environment.
"""

from django.http import Http404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLogEntry
from demo_control.demo_run import DemoRunError, current_status, start_demo_run, stop_demo_run
from demo_control.simulator import is_demo_tools_enabled, is_production_environment


class BaseDemoControlView(APIView):
    """
    Base view enforcing demo control feature flag, environment restriction,
    and Coach role-based access control.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        """Apply rules 1-3 before any handler runs."""
        # Rule 1: OFF unless env DEMO_TOOLS_ENABLED=true (default false). When off, every endpoint returns 404.
        if not is_demo_tools_enabled():
            raise Http404("Demo tools are disabled on this server.")

        # Rule 2: Refuse (403) when DJANGO_ENV=production.
        if is_production_environment():
            raise PermissionDenied("Demo tools are disabled in production environment.")

        # Standard authentication
        super().initial(request, *args, **kwargs)

        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated("Authentication credentials were not provided.")

        # Rule 3: Only role 'coach' may call it (403 for admin, driver and device).
        if getattr(request.user, "role", None) != "coach":
            raise PermissionDenied("Only coaches are permitted to control the demo simulator.")


class SimulatorStartView(BaseDemoControlView):
    """POST /api/demo/simulator/start/ — start one demo run on a map for a driver."""

    def post(self, request, *args, **kwargs):
        """Validate and start the run; answers 400/409 with a clear message when it cannot."""
        try:
            started = start_demo_run(request)
        except DemoRunError as error:
            return Response({"error": error.message}, status=error.status_code)

        # Rule 6: Write an AuditLogEntry on start
        AuditLogEntry.objects.create(
            actor=request.user,
            action=AuditLogEntry.Action.SIMULATOR_START,
            details=(f"Started demo on '{started['track_name']}' for {started['driver_name']}: "
                     f"{started['laps']} laps, pace {started['pace'] if started['pace_applied'] else 'n/a (built-in map)'}"),
        )
        return Response(started, status=status.HTTP_200_OK)


class SimulatorStopView(BaseDemoControlView):
    """POST /api/demo/simulator/stop/ — stop the run (idempotent) and clean up."""

    def post(self, request, *args, **kwargs):
        """Stop the simulator, close the demo session, unassign the demo device."""
        was_running = stop_demo_run(request)

        # Rule 6: Write an AuditLogEntry on stop
        AuditLogEntry.objects.create(
            actor=request.user,
            action=AuditLogEntry.Action.SIMULATOR_STOP,
            details="Stopped simulator" if was_running else "Stop requested (simulator was already stopped)",
        )
        return Response({"status": "stopped"}, status=status.HTTP_200_OK)


class SimulatorStatusView(BaseDemoControlView):
    """GET /api/demo/simulator/status/ — the run's state, lap, bridge status and last output lines."""

    def get(self, request, *args, **kwargs):
        """Return the status dictionary."""
        return Response(current_status(request), status=status.HTTP_200_OK)
