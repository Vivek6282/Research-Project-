"""
Trackside Virtual Lap Simulator — Backend Ingestion & Queue Dispatcher.
Manages asynchronous, non-blocking telemetry batching and posting to the Django REST API.
Includes retry mechanics, queue boundary handling, and clean flush on exit.
"""

import queue
import threading
import time
from datetime import datetime, timezone
import requests

from sim_config import BACKEND_URL, DEVICE_TOKEN, DEMO_ZONES, validate_backend_url

TELEMETRY_QUEUE = queue.Queue(maxsize=500)
SENT_COUNT = 0
FAILED_COUNT = 0
DROPPED_COUNT = 0
IN_FLIGHT_COUNT = 0
STATS_LOCK = threading.Lock()

LAST_WARNING_TIME = 0.0
WARNING_LOCK = threading.Lock()

BACKEND_WORKER_THREAD = None
SHUTDOWN_EVENT = threading.Event()


def log_rate_limited_warning(message_text):
    """
    Emits backend warning message at most once every 10 seconds to avoid spamming the console.
    Input: message_text (str).
    Output: None.
    """
    global LAST_WARNING_TIME
    current_time = time.time()
    with WARNING_LOCK:
        if current_time - LAST_WARNING_TIME >= 10.0:
            print(f"  [!] Backend Warning: {message_text}")
            LAST_WARNING_TIME = current_time


def build_telemetry_payload(g_value, speed_kmh, turn_name, lap_number, demo_zones=None, recorded_at=None):
    """
    Pure constructor building single telemetry reading dictionary for backend ingestion.
    Input: g_value (float), speed_kmh (float), turn_name (str), lap_number (int),
           demo_zones (dict or None), recorded_at (str or None).
    Output: Dictionary formatted for /api/sessions/<id>/telemetry/.
    """
    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    elif not recorded_at.endswith("Z"):
        if "+00:00" in recorded_at:
            recorded_at = recorded_at.replace("+00:00", "Z")
        else:
            recorded_at = recorded_at + "Z"

    resolved_zone_uuid = None
    if demo_zones and turn_name and turn_name.lower() != "straight":
        if turn_name in demo_zones:
            resolved_zone_uuid = demo_zones[turn_name]
        else:
            for corner_key, uuid_val in demo_zones.items():
                if corner_key.lower() == turn_name.lower():
                    resolved_zone_uuid = uuid_val
                    break

    return {
        "lateral_g": float(g_value),
        "speed_kmh": float(speed_kmh),
        "gps_lat": 0.0,
        "gps_lng": 0.0,
        "recorded_at": recorded_at,
        "lap_number": int(lap_number),
        "zone": resolved_zone_uuid,
    }


def enqueue_telemetry(reading_payload):
    """
    Enqueues telemetry payload in non-blocking manner. Drops reading if queue is saturated.
    Input: reading_payload (dict).
    Output: None.
    """
    global DROPPED_COUNT
    try:
        TELEMETRY_QUEUE.put_nowait(reading_payload)
    except queue.Full:
        with STATS_LOCK:
            DROPPED_COUNT += 1
        log_rate_limited_warning("Telemetry queue is full (500 items). Dropping readings.")


def _post_batch(batch_readings, session_id, device_token, backend_url):
    """
    Sends batch of readings to backend REST endpoint with timeout and exponential backoff retry.
    Input: batch_readings (list of dicts), session_id (str), device_token (str), backend_url (str).
    Output: True if successful, False if rejected or failed.
    """
    endpoint_url = f"{backend_url}/api/sessions/{session_id}/telemetry/"
    auth_headers = {
        "Authorization": f"Device-Token {device_token}",
        "Content-Type": "application/json",
    }

    max_retry_attempts = 3
    for attempt_number in range(1, max_retry_attempts + 1):
        try:
            http_response = requests.post(endpoint_url, headers=auth_headers, json=batch_readings, timeout=3)
            if http_response.status_code in (200, 201):
                return True
            elif http_response.status_code == 429:
                log_rate_limited_warning(f"Backend rate limited (HTTP 429). Attempt {attempt_number}/{max_retry_attempts}.")
                if attempt_number < max_retry_attempts:
                    time.sleep(0.5)
                    continue
                return False
            elif 400 <= http_response.status_code < 500:
                log_rate_limited_warning(f"Backend rejected batch with HTTP {http_response.status_code}: {http_response.text[:100]}")
                return False
            else:
                log_rate_limited_warning(f"Backend server error (HTTP {http_response.status_code}). Attempt {attempt_number}/{max_retry_attempts}.")
                if attempt_number < max_retry_attempts:
                    time.sleep(0.5)
                    continue
                return False
        except requests.exceptions.RequestException as network_err:
            log_rate_limited_warning(f"Network error sending batch: {network_err}. Attempt {attempt_number}/{max_retry_attempts}.")
            if attempt_number < max_retry_attempts:
                time.sleep(0.5)
                continue
            return False
    return False


def _backend_worker(session_id, device_token, backend_url):
    """
    Dedicated worker thread draining telemetry queue into batches of up to 10 or 1s intervals.
    Input: session_id (str), device_token (str), backend_url (str).
    Output: None.
    """
    global SENT_COUNT, FAILED_COUNT, IN_FLIGHT_COUNT

    while not SHUTDOWN_EVENT.is_set() or not TELEMETRY_QUEUE.empty():
        current_batch = []
        batch_start_timestamp = time.time()

        while len(current_batch) < 10:
            remaining_window = 1.0 - (time.time() - batch_start_timestamp)
            if remaining_window <= 0:
                break
            try:
                queued_reading = TELEMETRY_QUEUE.get(timeout=max(0.01, remaining_window))
                current_batch.append(queued_reading)
            except queue.Empty:
                if SHUTDOWN_EVENT.is_set():
                    break
                if time.time() - batch_start_timestamp >= 1.0:
                    break

        if not current_batch:
            continue

        with STATS_LOCK:
            IN_FLIGHT_COUNT += len(current_batch)

        batch_success = _post_batch(current_batch, session_id, device_token, backend_url)

        with STATS_LOCK:
            IN_FLIGHT_COUNT -= len(current_batch)
            if batch_success:
                SENT_COUNT += len(current_batch)
            else:
                FAILED_COUNT += len(current_batch)

        for _ in current_batch:
            TELEMETRY_QUEUE.task_done()


def start_backend_worker(session_id, device_token, backend_url=BACKEND_URL):
    """
    Launches the background daemon thread for asynchronous telemetry ingestion.
    Input: session_id (str), device_token (str), backend_url (str).
    Output: Thread object or None if invalid.
    """
    global BACKEND_WORKER_THREAD
    if not session_id or not device_token:
        return None
    if not validate_backend_url(backend_url):
        print(f"  [!] Refusing backend posting: BACKEND_URL '{backend_url}' must start with http:// or https:// and have a hostname.")
        return None
    BACKEND_WORKER_THREAD = threading.Thread(
        target=_backend_worker,
        args=(session_id, device_token, backend_url),
        daemon=True,
        name="BackendTelemetryWorker",
    )
    BACKEND_WORKER_THREAD.start()
    return BACKEND_WORKER_THREAD


def flush_backend_telemetry(timeout_seconds=5.0):
    """
    Stops worker thread, drains remaining queued items within timeout, and prints summary.
    Input: timeout_seconds (float).
    Output: None.
    """
    SHUTDOWN_EVENT.set()
    if BACKEND_WORKER_THREAD and BACKEND_WORKER_THREAD.is_alive():
        deadline = time.time() + timeout_seconds
        while time.time() < deadline and not TELEMETRY_QUEUE.empty():
            time.sleep(0.05)
        remaining_wait = max(0.1, deadline - time.time())
        BACKEND_WORKER_THREAD.join(timeout=remaining_wait)

    with STATS_LOCK:
        unsent_count = TELEMETRY_QUEUE.qsize() + IN_FLIGHT_COUNT
        sent_count = SENT_COUNT
        failed_count = FAILED_COUNT
        dropped_count = DROPPED_COUNT

    print(f"\nBackend summary: sent {sent_count}, failed {failed_count}, dropped {dropped_count}, unsent {unsent_count}")


def send_to_backend(session_id, g_value, zone_label, stage, speed_kmh, lap_number=1):
    """
    Enqueues reading for asynchronous dispatch to Django backend.
    Input: session_id (str), g_value (float), zone_label (str), stage (str), speed_kmh (float), lap_number (int).
    Output: None.
    """
    if not session_id or not DEVICE_TOKEN:
        return
    reading_payload = build_telemetry_payload(
        g_value=g_value,
        speed_kmh=speed_kmh,
        turn_name=zone_label,
        lap_number=lap_number,
        demo_zones=DEMO_ZONES,
    )
    enqueue_telemetry(reading_payload)
