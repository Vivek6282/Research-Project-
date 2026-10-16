"""
Trackside — Virtual Lap Simulator for Demo

Simulates a full lap around a virtual track, corner by corner, generating
realistic (not purely random) lateral-g values per turn — each corner has
its own characteristic force profile, matching the same zone thresholds
already used throughout the real system (Hairpin, Sweeper, Chicane).

Core requirement — Single Source of Truth:
This script synchronizes THREE destinations simultaneously for every single reading:
  1. Local WebSocket Broadcast: Streams live JSON
     {lap, zone, g_force, stage, speed_kmh, track_progress}
     to companion visualizations like track_visualization.html.
  2. USB Serial (Bridge ESP32): Relays lateral-g over ESP-NOW to the physical
     glove (LED + buzzer react live). Optional & fault-tolerant if hardware isn't attached.
  3. Django Backend (HTTP POST): Asynchronously batches and POSTs authenticated
     device telemetry without blocking the simulation loop so real
     Session/Telemetry/Alert records are stored and visible on the Coach/Driver dashboards.
"""

import time
import random
import argparse
import os
import sys
import math
import json
import threading
import asyncio
import queue
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# Try importing serial; pyserial might not be present in every environment
try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Try importing websockets
try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

import requests

# Load .env from script directory if present, else fallback to current directory
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Configuration from environment / defaults
SERIAL_PORT = os.getenv("SERIAL_PORT", "COM5")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
SESSION_ID = os.getenv("SESSION_ID", "")
WS_HOST = os.getenv("WS_HOST", "127.0.0.1")
WS_PORT = int(os.getenv("WS_PORT", "8765"))


def is_valid_uuid(val):
    """Checks whether a value is a valid UUID string representation."""
    if not isinstance(val, str):
        return False
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def validate_demo_zones(raw_demo_zones, session_id):
    """
    Validates DEMO_ZONES configuration.
    If DEMO_ZONES is set but is not valid JSON, or is not an object, or any value
    is not a UUID: print ONE clear warning at start-up naming the problem, and say
    'readings will be stored WITHOUT zones, so no alerts will be created'.
    If SESSION_ID is set but DEMO_ZONES is empty, print the same warning.
    """
    warning_suffix = "readings will be stored WITHOUT zones, so no alerts will be created."

    # If DEMO_ZONES is not set or empty string
    if raw_demo_zones is None or (isinstance(raw_demo_zones, str) and not raw_demo_zones.strip()):
        if session_id:
            print(f"  [!] Warning: DEMO_ZONES is empty: {warning_suffix}")
        return {}

    parsed = raw_demo_zones
    if isinstance(raw_demo_zones, str):
        try:
            parsed = json.loads(raw_demo_zones)
        except Exception:
            print(f"  [!] Warning: DEMO_ZONES is not valid JSON: {warning_suffix}")
            return {}

    if not isinstance(parsed, dict):
        print(f"  [!] Warning: DEMO_ZONES is not an object: {warning_suffix}")
        return {}

    if not parsed:
        if session_id:
            print(f"  [!] Warning: DEMO_ZONES is empty: {warning_suffix}")
        return {}

    for corner, zone_id in parsed.items():
        if not is_valid_uuid(zone_id):
            print(f"  [!] Warning: DEMO_ZONES value for '{corner}' is not a UUID: {warning_suffix}")
            return {}

    return parsed


# DEMO_ZONES mapping corner name to zone UUID (e.g. {"Hairpin":"uuid","Sweeper":"uuid","Chicane":"uuid"})
DEMO_ZONES_RAW = os.getenv("DEMO_ZONES")
try:
    if DEMO_ZONES_RAW:
        _d = json.loads(DEMO_ZONES_RAW) if isinstance(DEMO_ZONES_RAW, str) else DEMO_ZONES_RAW
        DEMO_ZONES = _d if isinstance(_d, dict) else {}
    else:
        DEMO_ZONES = {}
except Exception:
    DEMO_ZONES = {}

NUM_LAPS = 5
READING_DELAY_SECONDS = 0.2

# Default virtual track
TRACK = [
    {"name": "Hairpin",  "clean_range": (0.80, 1.00), "threshold": 1.15, "readings": 12},
    {"name": "Straight", "clean_range": (0.10, 0.30), "threshold": 99.0, "readings": 6},
    {"name": "Sweeper",  "clean_range": (1.10, 1.35), "threshold": 1.55, "readings": 14},
    {"name": "Straight", "clean_range": (0.10, 0.30), "threshold": 99.0, "readings": 6},
    {"name": "Chicane",  "clean_range": (0.95, 1.15), "threshold": 1.30, "readings": 10},
]

# ---------------------------------------------------------------------------
# WebSocket Server & Client State
# ---------------------------------------------------------------------------
CONNECTED_CLIENTS = set()
WS_LOOP = None


async def _ws_handler(websocket):
    """Register incoming browser clients and keep the socket open."""
    CONNECTED_CLIENTS.add(websocket)
    # Send an initial welcome/handshake payload
    try:
        init_payload = {
            "type": "connection_ack",
            "message": "Trackside Telemetry Stream Connected",
            "zones": [t["name"] for t in TRACK],
            "track_length": sum(t["readings"] for t in TRACK),
        }
        await websocket.send(json.dumps(init_payload))
        await websocket.wait_closed()
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)


async def _async_broadcast(message_str):
    """Broadcast JSON message to all active WebSocket clients."""
    if CONNECTED_CLIENTS:
        clients = list(CONNECTED_CLIENTS)
        await asyncio.gather(
            *[client.send(message_str) for client in clients],
            return_exceptions=True,
        )


def broadcast_reading(data):
    """
    Threadsafe dispatch from simulation loop to the background asyncio event loop.
    Dispatches JSON payload: {lap, zone, g_force, stage, speed_kmh, track_progress}.
    """
    global WS_LOOP
    if WS_LOOP and WS_LOOP.is_running():
        msg = json.dumps(data)
        asyncio.run_coroutine_threadsafe(_async_broadcast(msg), WS_LOOP)


async def _run_ws_server(host, port):
    """Asyncio runner for websockets.serve."""
    global WS_LOOP
    WS_LOOP = asyncio.get_running_loop()
    async with websockets.serve(_ws_handler, host, port):
        print(f"  [OK] WebSocket telemetry broadcaster active on ws://{host}:{port}")
        await asyncio.Future()  # run indefinitely


def start_websocket_server(host=WS_HOST, port=WS_PORT):
    """Starts the WebSocket server on a dedicated daemon background thread."""
    if not HAS_WEBSOCKETS:
        print("  [!] Warning: 'websockets' library is not installed. WebSocket broadcasting disabled.")
        return None

    def thread_target():
        try:
            asyncio.run(_run_ws_server(host, port))
        except Exception as e:
            print(f"  [!] WebSocket server error: {e}")

    t = threading.Thread(target=thread_target, daemon=True, name="TelemetryWebSocketBroadcaster")
    t.start()
    time.sleep(0.3)  # Brief yield to allow loop initialization
    return t


# ---------------------------------------------------------------------------
# Backend Asynchronous Ingestion & Pure Functions
# ---------------------------------------------------------------------------
def build_telemetry_payload(g_value, speed_kmh, turn_name, lap_number, demo_zones=None, recorded_at=None):
    """
    Pure function to construct a single telemetry reading payload for backend ingestion.

    Parameters:
    - g_value (float): Lateral g-force.
    - speed_kmh (float): Speed in km/h.
    - turn_name (str): Corner/zone name (e.g. 'Hairpin', 'Straight').
    - lap_number (int): 1-based lap number.
    - demo_zones (dict, optional): Mapping of corner name to zone UUID.
    - recorded_at (str, optional): ISO 8601 UTC timestamp ending in 'Z'.

    Returns:
    dict: Formatted telemetry reading payload.
    """
    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    elif not recorded_at.endswith("Z"):
        if "+00:00" in recorded_at:
            recorded_at = recorded_at.replace("+00:00", "Z")
        else:
            recorded_at = recorded_at + "Z"

    zone_uuid = None
    if demo_zones and turn_name and turn_name.lower() != "straight":
        if turn_name in demo_zones:
            zone_uuid = demo_zones[turn_name]
        else:
            for k, v in demo_zones.items():
                if k.lower() == turn_name.lower():
                    zone_uuid = v
                    break

    return {
        "lateral_g": float(g_value),
        "speed_kmh": float(speed_kmh),
        # simulated; real GPS comes with the kart unit
        "gps_lat": 0.0,
        "gps_lng": 0.0,
        "recorded_at": recorded_at,
        "lap_number": int(lap_number),
        "zone": zone_uuid,
    }


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


def log_rate_limited_warning(msg):
    """Prints warning at most once per 10 seconds, never one per reading."""
    global LAST_WARNING_TIME
    now = time.time()
    with WARNING_LOCK:
        if now - LAST_WARNING_TIME >= 10.0:
            print(f"  [!] Backend Warning: {msg}")
            LAST_WARNING_TIME = now


def enqueue_telemetry(payload):
    """
    Non-blocking enqueue for backend ingestion.
    Drops the reading if the queue is full and increments DROPPED_COUNT.
    """
    global DROPPED_COUNT
    try:
        TELEMETRY_QUEUE.put_nowait(payload)
    except queue.Full:
        with STATS_LOCK:
            DROPPED_COUNT += 1
        log_rate_limited_warning("Telemetry queue is full (500 items). Dropping readings.")


def _post_batch(batch, session_id, device_token, backend_url):
    """
    POSTs a batch of telemetry readings to the backend.
    - URL: /api/sessions/<SESSION_ID>/telemetry/
    - Header: 'Authorization: Device-Token <token>'
    - Timeout: 3 seconds.
    - Retries twice with 0.5s pause on network errors or 429.
    - Does not retry 4xx errors except 429.
    """
    url = f"{backend_url}/api/sessions/{session_id}/telemetry/"
    headers = {
        "Authorization": f"Device-Token {device_token}",
        "Content-Type": "application/json",
    }

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(url, headers=headers, json=batch, timeout=3)
            if resp.status_code in (200, 201):
                return True
            elif resp.status_code == 429:
                log_rate_limited_warning(f"Backend rate limited (HTTP 429). Attempt {attempt}/{max_attempts}.")
                if attempt < max_attempts:
                    time.sleep(0.5)
                    continue
                return False
            elif 400 <= resp.status_code < 500:
                log_rate_limited_warning(f"Backend rejected batch with HTTP {resp.status_code}: {resp.text[:100]}")
                return False
            else:
                log_rate_limited_warning(f"Backend server error (HTTP {resp.status_code}). Attempt {attempt}/{max_attempts}.")
                if attempt < max_attempts:
                    time.sleep(0.5)
                    continue
                return False
        except requests.exceptions.RequestException as e:
            log_rate_limited_warning(f"Network error sending batch: {e}. Attempt {attempt}/{max_attempts}.")
            if attempt < max_attempts:
                time.sleep(0.5)
                continue
            return False
    return False


def _backend_worker(session_id, device_token, backend_url):
    """
    Single daemon worker thread that batches up to 10 readings or 1 second,
    whichever comes first, and posts them to the backend.
    """
    global SENT_COUNT, FAILED_COUNT, IN_FLIGHT_COUNT

    while not SHUTDOWN_EVENT.is_set() or not TELEMETRY_QUEUE.empty():
        batch = []
        start_time = time.time()

        while len(batch) < 10:
            remaining = 1.0 - (time.time() - start_time)
            if remaining <= 0:
                break
            try:
                item = TELEMETRY_QUEUE.get(timeout=max(0.01, remaining))
                batch.append(item)
            except queue.Empty:
                if SHUTDOWN_EVENT.is_set():
                    break
                if time.time() - start_time >= 1.0:
                    break

        if not batch:
            continue

        with STATS_LOCK:
            IN_FLIGHT_COUNT += len(batch)

        success = _post_batch(batch, session_id, device_token, backend_url)

        with STATS_LOCK:
            IN_FLIGHT_COUNT -= len(batch)
            if success:
                SENT_COUNT += len(batch)
            else:
                FAILED_COUNT += len(batch)

        for _ in batch:
            TELEMETRY_QUEUE.task_done()


def start_backend_worker(session_id, device_token, backend_url=BACKEND_URL):
    """Starts the background worker thread for non-blocking backend telemetry ingestion."""
    global BACKEND_WORKER_THREAD
    if not session_id or not device_token:
        return None
    BACKEND_WORKER_THREAD = threading.Thread(
        target=_backend_worker,
        args=(session_id, device_token, backend_url),
        daemon=True,
        name="BackendTelemetryWorker",
    )
    BACKEND_WORKER_THREAD.start()
    return BACKEND_WORKER_THREAD


def flush_backend_telemetry(timeout=5.0):
    """
    Signals worker to stop, waits up to timeout seconds to flush remaining queue,
    and prints summary: sent N, failed M, dropped K, unsent U.
    where U = readings still queued or in flight when the program exits.
    """
    SHUTDOWN_EVENT.set()
    if BACKEND_WORKER_THREAD and BACKEND_WORKER_THREAD.is_alive():
        end_time = time.time() + timeout
        while time.time() < end_time and not TELEMETRY_QUEUE.empty():
            time.sleep(0.05)
        remaining_timeout = max(0.1, end_time - time.time())
        BACKEND_WORKER_THREAD.join(timeout=remaining_timeout)

    with STATS_LOCK:
        unsent = TELEMETRY_QUEUE.qsize() + IN_FLIGHT_COUNT
        sent = SENT_COUNT
        failed = FAILED_COUNT
        dropped = DROPPED_COUNT

    print(f"\nBackend summary: sent {sent}, failed {failed}, dropped {dropped}, unsent {unsent}")


def send_to_backend(session_id, g_value, zone_label, stage, speed_kmh, lap_number=1):
    """Enqueues reading for non-blocking asynchronous dispatch to Django backend."""
    if not session_id or not DEVICE_TOKEN:
        return
    payload = build_telemetry_payload(
        g_value=g_value,
        speed_kmh=speed_kmh,
        turn_name=zone_label,
        lap_number=lap_number,
        demo_zones=DEMO_ZONES,
    )
    enqueue_telemetry(payload)


# ---------------------------------------------------------------------------
# Backend & Hardware Integration
# ---------------------------------------------------------------------------
def fetch_zones_for_session(session_id, admin_token=None):
    """
    Fetches real zone thresholds from the backend and updates TRACK.
    Must never block start-up for more than 1 second (timeout 1 s, no retry).
    If it times out, print one notice and continue.
    """
    if not session_id:
        return

    print("Fetching actual track zones from backend...")
    headers = {}
    if admin_token:
        headers["Authorization"] = f"Bearer {admin_token}"

    auth_headers = headers if admin_token else {"Authorization": f"Device-Token {DEVICE_TOKEN}"}
    start_time = time.time()
    total_timeout = 1.0

    try:
        remaining = total_timeout - (time.time() - start_time)
        if remaining <= 0:
            print("  [!] Notice: Fetching session zones timed out (1s). Continuing with default thresholds.")
            return

        res = requests.get(
            f"{BACKEND_URL}/api/sessions/{session_id}/",
            headers=auth_headers,
            timeout=max(0.001, remaining),
        )
        if res.status_code != 200:
            print(f"  [!] Could not fetch session (status {res.status_code}). Using default thresholds.")
            return

        session_data = res.json()
        track_id = session_data.get("track")
        if not track_id:
            return

        remaining = total_timeout - (time.time() - start_time)
        if remaining <= 0:
            print("  [!] Notice: Fetching session zones timed out (1s). Continuing with default thresholds.")
            return

        z_res = requests.get(
            f"{BACKEND_URL}/api/tracks/{track_id}/zones/",
            headers=auth_headers,
            timeout=max(0.001, remaining),
        )
        if z_res.status_code == 200:
            data = z_res.json()
            zones = data.get("results", data) if isinstance(data, dict) else data

            for zone in zones:
                z_name = zone.get("label", "")
                z_thresh = zone.get("threshold_g")

                for turn in TRACK:
                    if turn["name"].lower() == z_name.lower():
                        old = turn["threshold"]
                        turn["threshold"] = z_thresh
                        print(f"  -> Updated {turn['name']} threshold: {old}g -> {z_thresh}g")
    except requests.exceptions.Timeout:
        print("  [!] Notice: Fetching session zones timed out (1s). Continuing with default thresholds.")
        return
    except Exception as e:
        print(f"  [!] Failed to fetch zones: {e}")


def create_session(admin_token):
    """Creates a new performance session automatically via admin JWT."""
    print("Creating new session automatically...")
    headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        res = requests.get(f"{BACKEND_URL}/api/tracks/", headers=headers)
        res.raise_for_status()
        data = res.json()
        tracks = data.get("results", data) if isinstance(data, dict) else data
        if not tracks:
            print("  [!] No tracks found in backend.")
            sys.exit(1)
        track_id = tracks[0]["id"]

        res = requests.get(f"{BACKEND_URL}/api/auth/users/", headers=headers)
        res.raise_for_status()
        data = res.json()
        users = data.get("results", data) if isinstance(data, dict) else data
        drivers = [u for u in users if u.get("role") == "driver"]
        if not drivers:
            print("  [!] No drivers found in backend.")
            sys.exit(1)
        driver_id = drivers[0]["id"]

        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "driver": driver_id,
            "track": track_id,
            "mode": "performance",
            "started_at": now,
        }

        res = requests.post(f"{BACKEND_URL}/api/sessions/", headers=headers, json=payload)
        res.raise_for_status()
        new_session = res.json()
        s_id = new_session["id"]
        print(f"  -> Created session: {s_id}")
        return s_id
    except Exception as e:
        print(f"  [!] Failed to create session: {e}")
        sys.exit(1)


def generate_turn_readings(turn, aggression):
    """Generates realistic lateral-g readings for a given corner."""
    readings = []
    low, high = turn["clean_range"]
    peak = random.uniform(low, high) * aggression
    n = turn["readings"]
    for i in range(n):
        shape = math.sin(math.pi * i / (n - 1)) if n > 1 else 1.0
        noise = random.uniform(-0.04, 0.04)
        g = max(0.05, peak * shape + noise)
        readings.append(round(g, 2))
    return readings


def generate_speed(zone_name, g_value):
    """Derives realistic kart speed (km/h) for the zone and lateral-g."""
    name = zone_name.lower()
    if "hairpin" in name:
        base = 52.0
    elif "sweeper" in name:
        base = 92.0
    elif "chicane" in name:
        base = 68.0
    else:  # Straight
        base = 120.0
    variation = random.uniform(-3.5, 3.5)
    speed = max(35.0, base - (g_value * 5.0) + variation)
    return round(speed, 1)


def classify_stage(g_value, threshold):
    """Maps lateral-g value to the 3-stage warning system."""
    if g_value >= threshold:
        return "INTERVENE"
    elif g_value >= threshold * 0.82:
        return "MONITORING"
    return "NOMINAL"


def send_to_bridge(ser, g_value, stage=None):
    """Fault-tolerant dispatch of g-force over USB Serial to Bridge ESP32."""
    if not ser:
        return
    try:
        if stage:
            ser.write(f"{g_value},{stage}\n".encode())
        else:
            ser.write(f"{g_value}\n".encode())
    except Exception as e:
        print(f"  [!] Serial send failed: {e}")


# ---------------------------------------------------------------------------
# Lap Runner
# ---------------------------------------------------------------------------
def run_lap(ser, session_id, lap_number, total_laps, delay):
    """
    Executes one lap around the track.
    Calculates track_progress (0.0 to 1.0) and broadcasts simultaneously
    to WebSocket, Serial, and Backend.
    """
    print(f"\n===== LAP {lap_number}{f' / {total_laps}' if total_laps > 0 else ''} =====")
    total_readings_in_lap = sum(turn["readings"] for turn in TRACK)
    current_reading_idx = 0

    for turn in TRACK:
        aggression = random.choices(
            [0.85, 1.0, 1.35],
            weights=[0.4, 0.4, 0.2],
        )[0]
        readings = generate_turn_readings(turn, aggression)
        peak_g = max(readings)
        peak_stage = classify_stage(peak_g, turn["threshold"])
        print(f"  -> {turn['name']:10s} | peak {peak_g:.2f}g | {peak_stage}")

        for g in readings:
            stage = classify_stage(g, turn["threshold"])
            speed_kmh = generate_speed(turn["name"], g)

            # Continuous track progress from 0.0 to 1.0
            track_progress = round(current_reading_idx / max(1, total_readings_in_lap), 4)
            current_reading_idx += 1

            # Exact JSON payload required by WebSocket client
            payload = {
                "lap": lap_number,
                "zone": turn["name"],
                "g_force": g,
                "stage": stage,
                "speed_kmh": speed_kmh,
                "track_progress": track_progress,
                "threshold": turn["threshold"],
            }

            # 1. Broadcast over local WebSocket (Companion track_visualization.html)
            broadcast_reading(payload)

            # 2. Output to physical Bridge ESP32 via Serial (if connected)
            send_to_bridge(ser, g, stage)

            # 3. Post to backend HTTP REST API (if session configured)
            send_to_backend(session_id, g, turn["name"], stage, speed_kmh, lap_number=lap_number)

            time.sleep(delay)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Trackside Virtual Lap Simulator with Live WebSocket Telemetry")
    parser.add_argument("--create-session", action="store_true", help="Automatically create a new session before running")
    parser.add_argument("--admin-token", type=str, help="Admin or Coach JWT Token for creating sessions")
    parser.add_argument("--dry-run", action="store_true", help="Skip connecting to Serial Port entirely")
    parser.add_argument("--laps", type=int, default=NUM_LAPS, help=f"Number of laps to run (default: {NUM_LAPS}, 0 for continuous)")
    parser.add_argument("--continuous", action="store_true", help="Run laps continuously until stopped with Ctrl+C")
    parser.add_argument("--delay", type=float, default=READING_DELAY_SECONDS, help=f"Delay between readings in seconds (default: {READING_DELAY_SECONDS})")
    parser.add_argument("--ws-port", type=int, default=WS_PORT, help=f"Port for local WebSocket telemetry broadcaster (default: {WS_PORT})")
    parser.add_argument("--ws-host", type=str, default=WS_HOST, help=f"Host for local WebSocket telemetry broadcaster (default: {WS_HOST})")
    args = parser.parse_args()

    global SESSION_ID, DEMO_ZONES
    if args.create_session:
        if not args.admin_token:
            print("Error: --create-session requires --admin-token to authenticate.")
            sys.exit(1)
        SESSION_ID = create_session(args.admin_token)

    DEMO_ZONES = validate_demo_zones(DEMO_ZONES_RAW, SESSION_ID)

    # Informative warnings for optional backend components
    if not SESSION_ID:
        print("  [i] Notice: No SESSION_ID configured.")
        print("      Telemetry will not be stored in backend, but will broadcast over WebSocket and Serial.")
    if not DEVICE_TOKEN:
        print("  [i] Notice: No DEVICE_TOKEN configured. Backend POSTs will be skipped.")

    fetch_zones_for_session(SESSION_ID, admin_token=args.admin_token)

    # Start non-blocking backend worker if credentials exist
    if SESSION_ID and DEVICE_TOKEN:
        start_backend_worker(SESSION_ID, DEVICE_TOKEN, BACKEND_URL)

    # 1. Start lightweight local WebSocket server
    print("\nStarting local WebSocket telemetry broadcaster...")
    ws_thread = start_websocket_server(host=args.ws_host, port=args.ws_port)
    if ws_thread:
        print(f"  [i] Open the visualizer: Coach Settings > Open Live Demo Visualizer, or frontend/public/demo/track_visualization.html")

    # 2. Setup Bridge ESP32 Serial connection (Fault-Tolerant)
    ser = None
    if not args.dry_run:
        if not HAS_SERIAL:
            print("  [!] 'pyserial' not installed. Continuing in Serial-free mode.")
        else:
            print(f"Connecting to Bridge ESP32 on {SERIAL_PORT}...")
            try:
                ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
                time.sleep(2)
                print(f"  [OK] Connected to Bridge ESP32 on {SERIAL_PORT}.")
            except Exception as e:
                print(f"  [!] Warning: Bridge ESP32 not detected on {SERIAL_PORT} ({e}).")
                print("      Continuing simulation with WebSocket broadcaster and backend ingestion.\n")
                ser = None
    else:
        print("  [Dry Run] Skipping Serial connection.")

    # 3. Run Lap Simulation
    target_laps = 0 if args.continuous else args.laps
    lap = 1
    print("\n" + "=" * 60)
    print(" TRACKSIDE VIRTUAL LAP SIMULATOR -- RUNNING")
    print(f" Target Laps: {'Infinite (Continuous)' if target_laps == 0 else target_laps}")
    print(f" Reading Interval: {args.delay}s")
    print(f" WebSocket Endpoint: ws://{args.ws_host}:{args.ws_port}")
    print("=" * 60 + "\n")

    try:
        while True:
            run_lap(ser, SESSION_ID, lap, target_laps, args.delay)
            lap += 1
            if target_laps > 0 and lap > target_laps:
                break
    except KeyboardInterrupt:
        print("\n[!] Simulation halted by user.")
    finally:
        if ser:
            try:
                ser.close()
            except Exception:
                pass
        # Flush backend queue (wait up to 5s) and print summary
        flush_backend_telemetry(timeout=5.0)
        print("\nSimulation session finished.")
        print("Check 'track_visualization.html' and Coach/Driver dashboards for results.")


if __name__ == "__main__":
    main()
