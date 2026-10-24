"""
Trackside — Driver consent checks (Phase 2.0).

Phone-sensor and biometric data may only be recorded for a driver whose consent
the academy has recorded. Other roles never carry such data.
"""

from rest_framework import exceptions

CONSENT_MISSING = "Consent for this driver is not recorded. Ask an admin to record it before sending this data."


def has_consent(driver) -> bool:
    """True when the academy has recorded this driver's consent."""
    return driver is not None and getattr(driver, "consent_recorded_at", None) is not None


def require_consent(driver) -> None:
    """Refuse (403) when the driver's consent is not recorded."""
    if not has_consent(driver):
        raise exceptions.PermissionDenied(CONSENT_MISSING)
