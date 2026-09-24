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
  3. Django Backend (HTTP POST): POSTs authenticated device telemetry so real
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

load_dotenv()

# Configuration from environment / defaults
SERIAL_PORT = os.getenv("SERIAL_PORT", "COM5")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
SESSION_ID = os.getenv("SESSION_ID", "")
WS_HOST = os.getenv("WS_HOST", "127.0.0.1")
WS_PORT = int(os.getenv("WS_PORT", "8765"))

NUM_LAPS = 5
READING_DELAY_SECONDS = 0.2

# Default virtual track
TRACK = [
    {"name": "Hairpin",  "clean_range": (0.80, 1.00), "threshold": 1.15, "readings": 12},
    {"name": "Straight",  "clean_range": (0.10, 0.30), "threshold": 99.0, "readings": 6},
    {"name": "Sweeper",  "clean_range": (1.10, 1.35), "threshold": 1.55, "readings": 14},
    {"name": "Straight",  "clean_range": (0.10, 0.30), "threshold": 99.0, "readings": 6},
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
# Backend & Hardware Integration
# ---------------------------------------------------------------------------
def fetch_zones_for_session(session_id, admin_token=None):
    """Fetches real zone thresholds from the backend and updates TRACK."""
    if not session_id:
        return

    print("Fetching actual track zones from backend...")
    headers = {}
    if admin_token:
        headers["Authorization"] = f"Bearer {admin_token}"

    auth_headers = headers if admin_token else {"Authorization": f"Device-Token {DEVICE_TOKEN}"}

    try:
        res = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/", headers=auth_headers, timeout=5)
        if res.status_code != 200:
            print(f"  [!] Could not fetch session (status {res.status_code}). Using default thresholds.")
            return

        session_data = res.json()
        track_id = session_data.get("track")
        if not track_id:
            return

        z_res = requests.get(f"{BACKEND_URL}/api/tracks/{track_id}/zones/", headers=auth_headers, timeout=5)
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

        from datetime import datetime, timezone
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


def send_to_bridge(ser, g_value):
    """Fault-tolerant dispatch of g-force over USB Serial to Bridge ESP32."""
    if not ser:
        return
    try:
        ser.write(f"{g_value}\n".encode())
    except Exception as e:
        print(f"  [!] Serial send failed: {e}")


def send_to_backend(session_id, g_value, zone_label, stage, speed_kmh):
    """Dispatches reading to Django backend REST endpoint."""
    if not session_id or not DEVICE_TOKEN:
        return
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/sessions/{session_id}/telemetry/",
            headers={"Authorization": f"Device-Token {DEVICE_TOKEN}"},
            json={
                "lateral_g": g_value,
                "speed_kmh": speed_kmh,
                "gps_lat": 0.0,
                "gps_lng": 0.0,
            },
            timeout=2,
        )
        if response.status_code not in (200, 201):
            print(f"  [!] Backend rejected reading: {response.status_code} {response.text[:100]}")
    except Exception as e:
        print(f"  [!] Backend POST failed: {e}")


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
            send_to_bridge(ser, g)

            # 3. Post to backend HTTP REST API (if session configured)
            send_to_backend(session_id, g, turn["name"], stage, speed_kmh)

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

    global SESSION_ID
    if args.create_session:
        if not args.admin_token:
            print("Error: --create-session requires --admin-token to authenticate.")
            sys.exit(1)
        SESSION_ID = create_session(args.admin_token)

    # Informative warnings for optional backend components
    if not SESSION_ID:
        print("  [i] Notice: No SESSION_ID configured.")
        print("      Telemetry will not be stored in backend, but will broadcast over WebSocket and Serial.")
    if not DEVICE_TOKEN:
        print("  [i] Notice: No DEVICE_TOKEN configured. Backend POSTs will be skipped.")

    fetch_zones_for_session(SESSION_ID, admin_token=args.admin_token)

    # 1. Start lightweight local WebSocket server
    print("\nStarting local WebSocket telemetry broadcaster...")
    ws_thread = start_websocket_server(host=args.ws_host, port=args.ws_port)
    if ws_thread:
        print(f"  [i] Open 'track_visualization.html' in your browser to view the live synchronized visualizer.")

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
        print("\nSimulation session finished.")
        print("Check 'track_visualization.html' and Coach/Driver dashboards for results.")


if __name__ == "__main__":
    main()
