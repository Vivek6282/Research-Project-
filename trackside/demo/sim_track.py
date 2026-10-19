"""
Trackside Virtual Lap Simulator — Track Definition and Corner Dynamics.
Defines virtual track layout, realistic lateral g-force generation, speed calculations,
and 3-stage warning system classification.
"""

import math
import random
import sys
import time
from datetime import datetime, timezone
import requests

from sim_config import BACKEND_URL, DEVICE_TOKEN

# Default virtual track layout with target clean g-force ranges and alert thresholds
TRACK = [
    {"name": "Hairpin",  "clean_range": (0.80, 1.00), "threshold": 1.15, "readings": 12},
    {"name": "Straight", "clean_range": (0.10, 0.30), "threshold": 99.0, "readings": 6},
    {"name": "Sweeper",  "clean_range": (1.10, 1.35), "threshold": 1.55, "readings": 14},
    {"name": "Straight", "clean_range": (0.10, 0.30), "threshold": 99.0, "readings": 6},
    {"name": "Chicane",  "clean_range": (0.95, 1.15), "threshold": 1.30, "readings": 10},
]


def generate_turn_readings(corner_info, driver_aggression):
    """
    Generates realistic lateral g-force measurements across a corner arc.
    Input: corner_info dict with clean_range and readings count, driver_aggression float.
    Output: List of float lateral-g readings.
    """
    generated_readings = []
    min_force, max_force = corner_info["clean_range"]
    peak_force = random.uniform(min_force, max_force) * driver_aggression
    point_count = corner_info["readings"]
    for point_idx in range(point_count):
        arc_shape = math.sin(math.pi * point_idx / (point_count - 1)) if point_count > 1 else 1.0
        sensor_noise = random.uniform(-0.04, 0.04)
        measured_g = max(0.05, peak_force * arc_shape + sensor_noise)
        generated_readings.append(round(measured_g, 2))
    return generated_readings


def generate_speed(zone_label, lateral_g_force):
    """
    Computes realistic kart velocity in km/h based on zone profile and lateral acceleration.
    Input: zone_label (str), lateral_g_force (float).
    Output: Speed in km/h rounded to 1 decimal place.
    """
    normalized_label = zone_label.lower()
    if "hairpin" in normalized_label:
        baseline_speed = 52.0
    elif "sweeper" in normalized_label:
        baseline_speed = 92.0
    elif "chicane" in normalized_label:
        baseline_speed = 68.0
    else:  # Straight
        baseline_speed = 120.0
    random_fluctuation = random.uniform(-3.5, 3.5)
    derived_speed = max(35.0, baseline_speed - (lateral_g_force * 5.0) + random_fluctuation)
    return round(derived_speed, 1)


def classify_stage(lateral_g_force, safe_threshold_g):
    """
    Maps measured lateral g-force against safe threshold to 3-stage warning system.
    Input: lateral_g_force (float), safe_threshold_g (float).
    Output: String stage: 'NOMINAL', 'MONITORING', or 'INTERVENE'.
    """
    if lateral_g_force >= safe_threshold_g:
        return "INTERVENE"
    elif lateral_g_force >= safe_threshold_g * 0.82:
        return "MONITORING"
    return "NOMINAL"


def fetch_zones_for_session(session_id, admin_token=None, custom_limits=None, corner_sources=None):
    """
    Queries backend REST API for zone thresholds associated with the active session's track.
    Times out in 1.0s without blocking simulation start.
    Input: session_id (str), admin_token (str or None), custom_limits (dict), corner_sources (dict).
    Output: Updates TRACK thresholds in-place.
    """
    if not session_id:
        return

    if custom_limits is None:
        custom_limits = {}
    if corner_sources is None:
        corner_sources = {}

    print("Fetching actual track zones from backend...")
    auth_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {"Authorization": f"Device-Token {DEVICE_TOKEN}"}
    start_timestamp = time.time()
    total_timeout_seconds = 1.0

    try:
        remaining_timeout = total_timeout_seconds - (time.time() - start_timestamp)
        if remaining_timeout <= 0:
            print("  [!] Notice: Fetching session zones timed out (1s). Continuing with default thresholds.")
            return

        session_response = requests.get(
            f"{BACKEND_URL}/api/sessions/{session_id}/",
            headers=auth_headers,
            timeout=max(0.001, remaining_timeout),
        )
        if session_response.status_code != 200:
            print(f"  [!] Could not fetch session (status {session_response.status_code}). Using default thresholds.")
            return

        session_payload = session_response.json()
        track_identifier = session_payload.get("track")
        if not track_identifier:
            return

        remaining_timeout = total_timeout_seconds - (time.time() - start_timestamp)
        if remaining_timeout <= 0:
            print("  [!] Notice: Fetching session zones timed out (1s). Continuing with default thresholds.")
            return

        zones_response = requests.get(
            f"{BACKEND_URL}/api/tracks/{track_identifier}/zones/",
            headers=auth_headers,
            timeout=max(0.001, remaining_timeout),
        )
        if zones_response.status_code == 200:
            zones_data = zones_response.json()
            zone_records = zones_data.get("results", zones_data) if isinstance(zones_data, dict) else zones_data

            for zone_record in zone_records:
                zone_name = zone_record.get("label", "")
                threshold_value = zone_record.get("threshold_g")
                if threshold_value is None:
                    continue

                for turn in TRACK:
                    if turn["name"].lower() == zone_name.lower():
                        canonical_corner_name = turn["name"]
                        if canonical_corner_name in custom_limits:
                            print(f"  -> Fetched {canonical_corner_name} zone ({threshold_value}g), but custom limit {custom_limits[canonical_corner_name]:.2f}g takes precedence")
                        else:
                            previous_threshold = turn["threshold"]
                            turn["threshold"] = float(threshold_value)
                            corner_sources[canonical_corner_name] = "backend zone"
                            print(f"  -> Updated {turn['name']} threshold: {previous_threshold}g -> {threshold_value}g")
    except requests.exceptions.Timeout:
        print("  [!] Notice: Fetching session zones timed out (1s). Continuing with default thresholds.")
    except Exception as exc:
        print(f"  [!] Failed to fetch zones: {exc}")


def create_session(admin_token):
    """
    Creates a new driving session automatically on backend using admin JWT.
    Input: admin_token (str).
    Output: Created session UUID string.
    """
    print("Creating new session automatically...")
    request_headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        tracks_response = requests.get(f"{BACKEND_URL}/api/tracks/", headers=request_headers, timeout=3)
        tracks_response.raise_for_status()
        tracks_data = tracks_response.json()
        track_list = tracks_data.get("results", tracks_data) if isinstance(tracks_data, dict) else tracks_data
        if not track_list:
            print("  [!] No tracks found in backend.")
            sys.exit(1)
        target_track_id = track_list[0]["id"]

        users_response = requests.get(f"{BACKEND_URL}/api/auth/users/", headers=request_headers, timeout=3)
        users_response.raise_for_status()
        users_data = users_response.json()
        user_list = users_data.get("results", users_data) if isinstance(users_data, dict) else users_data
        driver_users = [user for user in user_list if user.get("role") == "driver"]
        if not driver_users:
            print("  [!] No drivers found in backend.")
            sys.exit(1)
        target_driver_id = driver_users[0]["id"]

        current_timestamp_iso = datetime.now(timezone.utc).isoformat()

        session_payload = {
            "driver": target_driver_id,
            "track": target_track_id,
            "mode": "performance",
            "started_at": current_timestamp_iso,
        }

        creation_response = requests.post(f"{BACKEND_URL}/api/sessions/", headers=request_headers, json=session_payload, timeout=3)
        creation_response.raise_for_status()
        created_session_data = creation_response.json()
        new_session_id = created_session_data["id"]
        print(f"  -> Created session: {new_session_id}")
        return new_session_id
    except Exception as exc:
        print(f"  [!] Failed to create session: {exc}")
        sys.exit(1)
