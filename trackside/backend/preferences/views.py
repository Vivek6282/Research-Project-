"""
Trackside — Preferences views.

Users can only read/update their own preferences — no access to other
users' preferences. Requirement #3 (IDOR): queryset always scoped to
request.user.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from preferences.models import UserPreference
from preferences.serializers import UserPreferenceSerializer


class MyPreferencesView(generics.RetrieveUpdateAPIView):
    """
    GET /api/preferences/me/ — get current user's preferences
    PUT/PATCH /api/preferences/me/ — update current user's preferences

    Always scoped to request.user — you can only see/edit your own.
    Creates default preferences on first access if none exist.
    """

    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Return the current user's preferences, creating defaults
        if they don't exist yet (first login).
        """
        preference, _created = UserPreference.objects.get_or_create(
            user=self.request.user,
            defaults={
                "font_size": UserPreference.FontSize.MEDIUM,
            },
        )

        return preference
