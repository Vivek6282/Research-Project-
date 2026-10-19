"""
Trackside Driving Sessions — Session CRUD Views.
This module provides endpoints for listing, creating, retrieving, updating,
and ending driving sessions with strict role-based access scoping.
"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminOrCoach
from driving_sessions.access import sessions_visible_to
from driving_sessions.serializers import SessionSerializer


class SessionListCreateView(generics.ListCreateAPIView):
    """
    GET /api/sessions/ — list sessions scoped by role.
    POST /api/sessions/ — driver starts a new driving session.

    Security:
    - Drivers only see their own sessions.
    - Devices only see sessions for their assigned driver.
    - Coaches and admins see all sessions.
    """

    serializer_class = SessionSerializer

    def get_permissions(self):
        """
        Returns permissions required for this endpoint.
        Input: None.
        Output: List with IsAuthenticated instance.
        """
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Returns sessions visible to the authenticated user.
        Input: None (uses request.user).
        Output: Scoped Session QuerySet with driver and track pre-fetched.
        """
        return sessions_visible_to(self.request.user).select_related("driver", "track")

    def perform_create(self, serializer):
        """
        Associates the session with the authenticated driver if the user is a driver.
        Input: Validated Session serializer.
        Output: None.
        """
        acting_user = self.request.user
        if acting_user.role == "driver":
            serializer.save(driver=acting_user)
        else:
            serializer.save()


class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/sessions/<uuid>/ — retrieve session details.
    PUT/PATCH/DELETE — update or terminate session (Admin or Coach only).

    Security:
    - Retrieval is scoped to authorized sessions.
    - Mutations are restricted to coaches and admins via IsAdminOrCoach.
    """

    serializer_class = SessionSerializer

    def get_permissions(self):
        """
        Enforces Admin/Coach role for mutations while allowing authenticated drivers to view.
        Input: None.
        Output: List of permission instances.
        """
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdminOrCoach()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Returns sessions visible to the user to prevent unauthorized access by UUID guess.
        Input: None.
        Output: Scoped Session QuerySet.
        """
        return sessions_visible_to(self.request.user)
