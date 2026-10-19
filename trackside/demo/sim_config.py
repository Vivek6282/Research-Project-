"""
Trackside Virtual Lap Simulator — Configuration and Validation Module.
Loads environment variables from demo/.env and provides validation helpers
for UUIDs, backend URLs, and demo zone mappings.
"""

import json
import os
import uuid
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment configuration from demo/.env if present
env_file_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)
else:
    load_dotenv()

# Communication and target endpoints
SERIAL_PORT = os.getenv("SERIAL_PORT", "COM5")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
SESSION_ID = os.getenv("SESSION_ID", "")
WS_HOST = "127.0.0.1"
WS_PORT = int(os.getenv("WS_PORT", "8765"))

# Allowed WebSocket origins (S6 security hardening)
raw_allowed_origins = os.getenv("WS_ALLOWED_ORIGINS", "")
if raw_allowed_origins.strip():
    WS_ALLOWED_ORIGINS = [origin.strip() for origin in raw_allowed_origins.split(",") if origin.strip()]
else:
    WS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "null", "file://"]

NUM_LAPS = 5
READING_DELAY_SECONDS = 0.2


def is_valid_uuid(candidate_string):
    """
    Checks whether candidate_string is a valid UUID string representation.
    Input: candidate_string (any).
    Output: True if valid UUID, False otherwise.
    """
    if not isinstance(candidate_string, str):
        return False
    try:
        uuid.UUID(candidate_string)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def validate_backend_url(target_url):
    """
    Validates that target_url starts with http:// or https:// and contains a valid hostname.
    Input: target_url (str).
    Output: True if valid URL, False otherwise (S8).
    """
    if not target_url or not isinstance(target_url, str):
        return False
    try:
        parsed_url = urlparse(target_url)
        return parsed_url.scheme in ("http", "https") and bool(parsed_url.hostname)
    except Exception:
        return False


def validate_demo_zones(raw_demo_zones, session_id):
    """
    Validates DEMO_ZONES mapping from corner names to UUIDs.
    Input: raw_demo_zones (dict or JSON string), session_id (str).
    Output: Validated dictionary mapping corner names to zone UUIDs.
    """
    warning_suffix = "readings will be stored WITHOUT zones, so no alerts will be created."

    if raw_demo_zones is None or (isinstance(raw_demo_zones, str) and not raw_demo_zones.strip()):
        if session_id:
            print(f"  [!] Warning: DEMO_ZONES is empty: {warning_suffix}")
        return {}

    parsed_zones = raw_demo_zones
    if isinstance(raw_demo_zones, str):
        try:
            parsed_zones = json.loads(raw_demo_zones)
        except Exception:
            print(f"  [!] Warning: DEMO_ZONES is not valid JSON: {warning_suffix}")
            return {}

    if not isinstance(parsed_zones, dict):
        print(f"  [!] Warning: DEMO_ZONES is not an object: {warning_suffix}")
        return {}

    if not parsed_zones:
        if session_id:
            print(f"  [!] Warning: DEMO_ZONES is empty: {warning_suffix}")
        return {}

    for corner_name, zone_uuid in parsed_zones.items():
        if not is_valid_uuid(zone_uuid):
            print(f"  [!] Warning: DEMO_ZONES value for '{corner_name}' is not a UUID: {warning_suffix}")
            return {}

    return parsed_zones


# Initial demo zones parsing
DEMO_ZONES_RAW = os.getenv("DEMO_ZONES")
try:
    if DEMO_ZONES_RAW:
        parsed_raw_dict = json.loads(DEMO_ZONES_RAW) if isinstance(DEMO_ZONES_RAW, str) else DEMO_ZONES_RAW
        DEMO_ZONES = parsed_raw_dict if isinstance(parsed_raw_dict, dict) else {}
    else:
        DEMO_ZONES = {}
except Exception:
    DEMO_ZONES = {}
