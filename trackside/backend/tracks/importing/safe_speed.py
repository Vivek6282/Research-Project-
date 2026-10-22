"""Trackside — Safe corner speed hint and the allowed corner-limit range (sprint karts)."""

import math

from tracks.models import Track

GRAVITY = 9.81
# Sprint-kart limits run from 0.3 to 1.5 g (the coach may set a low limit for a slow corner)
LIMIT_MIN_G = Track.KART_CLASS_FLOOR[Track.KartClass.SPRINT]
LIMIT_MAX_G = Track.KART_CLASS_CEILING[Track.KartClass.SPRINT]
# Starting value shown in the form; the user changes it per corner
DEFAULT_LIMIT_G = 1.25


def safe_speed_kmh(limit_g: float, radius_m: float) -> float:
    """Fastest speed (km/h) that keeps lateral g at the limit: sqrt(limit x 9.81 x radius)."""
    return math.sqrt(limit_g * GRAVITY * radius_m) * 3.6
