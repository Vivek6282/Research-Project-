"""
Trackside — The allowed payload of each device event type (Phase 2.0).

Every field is listed with its kind, whether it is required, and its range.
Unknown fields are refused, so a device cannot store arbitrary data.
"""

import json
import math
import uuid

MAX_PAYLOAD_BYTES = 8 * 1024
MAX_SAMPLE_ROWS = 400
MAX_SAMPLE_VALUES = 8

# field name -> (kind, required, minimum, maximum); for "text" the maximum is the length limit
LATITUDE = ("number", False, -90.0, 90.0)
LONGITUDE = ("number", False, -180.0, 180.0)
SPEED_KMH = ("number", False, 0.0, 200.0)

PAYLOAD_SCHEMAS = {
    "crash_suspected": {
        "lat": LATITUDE, "lng": LONGITUDE, "speed_before_kmh": SPEED_KMH,
        "peak_g": ("number", True, 0.0, 400.0), "saturated": ("bool", False, None, None),
        "raw_window": ("samples", False, None, None),
    },
    "lost_contact": {"last_lat": LATITUDE, "last_lng": LONGITUDE, "last_speed_kmh": SPEED_KMH},
    "heartbeat": {"firmware_version": ("text", False, None, 32), "battery_mv": ("number", False, 0.0, 10000.0)},
    "self_test_result": {"passed": ("bool", True, None, None), "details": ("text", False, None, 500),
                         "command_id": ("uuid", False, None, None)},
    "driver_ok": {"crash_event_id": ("uuid", True, None, None)},
}


def is_number(value) -> bool:
    """A real, finite number (true/false are not numbers here)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_samples(value) -> str:
    """Raw readings: a list of rows, each a short list of numbers. Returns an error text or ''."""
    if not isinstance(value, list) or len(value) > MAX_SAMPLE_ROWS:
        return f"must be a list of at most {MAX_SAMPLE_ROWS} rows"
    for row in value:
        if not isinstance(row, list) or not 1 <= len(row) <= MAX_SAMPLE_VALUES or not all(map(is_number, row)):
            return f"each row must be a list of 1 to {MAX_SAMPLE_VALUES} numbers"
    return ""


def check_field(kind, low, high, value) -> str:
    """Check one value against its kind and range. Returns an error text or ''."""
    if kind == "number":
        if not is_number(value) or not low <= value <= high:
            return f"must be a number from {low} to {high}"
    elif kind == "bool":
        if not isinstance(value, bool):
            return "must be true or false"
    elif kind == "text":
        if not isinstance(value, str) or len(value) > high:
            return f"must be text of at most {high} characters"
    elif kind == "uuid":
        try:
            uuid.UUID(str(value))
        except ValueError:
            return "must be an id (UUID)"
    elif kind == "samples":
        return check_samples(value)
    return ""


def payload_errors(event_type: str, payload) -> dict:
    """All problems with a payload as {field: message}; an empty dict means it is valid."""
    schema = PAYLOAD_SCHEMAS.get(event_type)
    if schema is None:
        return {}
    if not isinstance(payload, dict):
        return {"payload": "must be an object"}
    if len(json.dumps(payload).encode("utf-8")) > MAX_PAYLOAD_BYTES:
        return {"payload": f"must be at most {MAX_PAYLOAD_BYTES} bytes"}
    errors = {name: "is not allowed for this event type" for name in payload if name not in schema}
    for name, (kind, required, low, high) in schema.items():
        if name not in payload:
            if required:
                errors[name] = "is required"
            continue
        problem = check_field(kind, low, high, payload[name])
        if problem:
            errors[name] = problem
    return errors
