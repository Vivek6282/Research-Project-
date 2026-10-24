"""
Trackside — Who may send phone readings to a session (Phase 2.1).

A driver's own readings come from the phone page. They are accepted only when
the academy has recorded the driver's consent and the coach has set the session
to real time, so a stray phone cannot feed a simulator run.
"""

from rest_framework import exceptions, status

from academy.consent import require_consent
from driving_sessions.models import Session

NOT_REAL_TIME = "This session is set to Simulator. Ask the coach to start a real-time session for the phone."


class SessionNotRealTime(exceptions.APIException):
    """409: the session does not take phone readings."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = NOT_REAL_TIME


def check_phone_may_send(driver, session: Session) -> None:
    """Refuse (403 without consent, 409 for a simulator session); return quietly when the phone may send."""
    require_consent(driver)
    if session.data_source != Session.DataSource.REAL_TIME:
        raise SessionNotRealTime()
