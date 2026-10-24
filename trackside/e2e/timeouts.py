"""
Trackside E2E — One place for every wait in the Selenium suite.

Slow machines can raise these with environment variables instead of editing tests:
  TRACKSIDE_E2E_UI_TIMEOUT       seconds to wait for something to appear (default 10)
  TRACKSIDE_E2E_API_TIMEOUT      seconds for a direct API call made by a test (default 15)
  TRACKSIDE_E2E_ABSENCE_TIMEOUT  seconds to watch for something that must NOT appear (default 3)
"""

import os


def seconds_from_env(name: str, default: float) -> float:
    """Read a positive number of seconds from the environment, or use the default."""
    raw_value = os.environ.get(name, "").strip()
    try:
        value = float(raw_value) if raw_value else default
    except ValueError:
        raise ValueError(f"{name} must be a number of seconds, got {raw_value!r}") from None
    if value <= 0:
        raise ValueError(f"{name} must be above zero, got {value}")
    return value


UI_TIMEOUT_S = seconds_from_env("TRACKSIDE_E2E_UI_TIMEOUT", 10.0)
API_TIMEOUT_S = seconds_from_env("TRACKSIDE_E2E_API_TIMEOUT", 15.0)
ABSENCE_TIMEOUT_S = seconds_from_env("TRACKSIDE_E2E_ABSENCE_TIMEOUT", 3.0)
