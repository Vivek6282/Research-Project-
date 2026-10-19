"""
Trackside — Driving Sessions Access Control (S1).

Centralized authorization helpers enforcing strict DENY BY DEFAULT access scoping:
- driver -> own sessions only
- coach / admin -> all sessions
- device WITH assigned driver -> that driver's sessions only
- anything else (unassigned device, unknown role, unauthenticated/anonymous) -> .none() / False
"""

from typing import Union
from django.db.models import QuerySet
from driving_sessions.models import Session


def sessions_visible_to(user) -> QuerySet:
    """
    Returns a QuerySet of Session objects visible to the given user or device.
    Rule: DENY BY DEFAULT.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return Session.objects.none()

    role = getattr(user, "role", None)

    if role in ("coach", "admin"):
        return Session.objects.all()

    if role == "driver":
        return Session.objects.filter(driver=user)

    if role == "device":
        assigned_to = getattr(user, "assigned_to", None)
        if assigned_to:
            return Session.objects.filter(driver=assigned_to)
        return Session.objects.none()

    return Session.objects.none()


def can_access_session(user, session: Union[Session, str, None]) -> bool:
    """
    Returns True if user has authorization to view or interact with the specified session.
    Rule: DENY BY DEFAULT.
    Works with both Session instances and session UUID strings.
    """
    if not user or not getattr(user, "is_authenticated", False) or session is None:
        return False

    if isinstance(session, (str, bytes)):
        try:
            session_obj = Session.objects.select_related("driver").get(pk=session)
        except (Session.DoesNotExist, ValueError):
            return False
    else:
        session_obj = session

    role = getattr(user, "role", None)

    if role in ("coach", "admin"):
        return True

    if role == "driver":
        return session_obj.driver_id == user.id

    if role == "device":
        assigned_to = getattr(user, "assigned_to", None)
        if assigned_to:
            assigned_id = getattr(assigned_to, "id", assigned_to)
            return session_obj.driver_id == assigned_id
        return False

    return False
