"""Trackside — Close a driving session (shared by the finish endpoint and Coach demo runs)."""

from django.utils import timezone

from driving_sessions.models import Session


def close_session_if_open(session_id) -> bool:
    """Set ended_at to now only if it is still empty; returns True when this call closed it.

    One atomic UPDATE, so two callers at once cannot both write and the first time stays.
    """
    return Session.objects.filter(pk=session_id, ended_at__isnull=True).update(ended_at=timezone.now()) == 1
