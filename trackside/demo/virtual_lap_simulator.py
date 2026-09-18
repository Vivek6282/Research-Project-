"""
Trackside — Virtual Lap Simulator for Demo

Simulates a full lap around a virtual track, corner by corner, generating
realistic (not purely random) lateral-g values per turn — each corner has
its own characteristic force profile, matching the same zone thresholds
already used throughout the real system (Hairpin, Sweeper, Chicane).

This script does TWO things simultaneously for each reading:
  1. Sends the value over USB Serial to the Bridge ESP32, which relays it
     via real ESP-NOW to the physical glove (LED + buzzer react live).
  2. POSTs the same reading to the real Django backend as authenticated
     device telemetry, so a real Session/Telemetry/Alert gets stored and
     is viewable afterward on the actual Coach/Driver dashboards.
"""

import time
import random
import serial
import requests
import argparse
import os
import sys
import math
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment
SERIAL_PORT = os.getenv("SERIAL_PORT", "COM5")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
SESSION_ID = os.getenv("SESSION_ID", "")

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

def fetch_zones_for_session(session_id, admin_token=None):
    """Fetches real zone thresholds from the backend and updates TRACK."""
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
    """Creates a new performance session automatically."""
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
            "started_at": now
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

def classify_stage(g_value, threshold):
    if g_value >= threshold:
        return "INTERVENE"
    elif g_value >= threshold * 0.82:
        return "MONITORING"
    return "NOMINAL"

def send_to_bridge(ser, g_value):
    if not ser: return
    try:
        ser.write(f"{g_value}\n".encode())
    except Exception as e:
        print(f"  [!] Serial send failed: {e}")

def send_to_backend(session_id, g_value, zone_label, stage):
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/sessions/{session_id}/telemetry/",
            headers={"Authorization": f"Device-Token {DEVICE_TOKEN}"},
            json={
                "lateral_g": g_value,
                "speed_kmh": round(random.uniform(60, 110), 1),
                "gps_lat": 0.0,
                "gps_lng": 0.0,
            },
            timeout=2,
        )
        if response.status_code not in (200, 201):
            print(f"  [!] Backend rejected reading: {response.status_code} {response.text[:100]}")
    except Exception as e:
        print(f"  [!] Backend POST failed: {e}")

def run_lap(ser, session_id, lap_number):
    print(f"\n===== LAP {lap_number} =====")
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
            send_to_bridge(ser, g)
            send_to_backend(session_id, g, turn["name"], stage)
            time.sleep(READING_DELAY_SECONDS)

def main():
    parser = argparse.ArgumentParser(description="Virtual Lap Simulator")
    parser.add_argument("--create-session", action="store_true", help="Automatically create a new session before running")
    parser.add_argument("--admin-token", type=str, help="Admin or Coach JWT Token for creating sessions")
    parser.add_argument("--dry-run", action="store_true", help="Skip connecting to Serial Port")
    args = parser.parse_args()

    global SESSION_ID
    if args.create_session:
        if not args.admin_token:
            print("Error: --create-session requires --admin-token to authenticate.")
            sys.exit(1)
        SESSION_ID = create_session(args.admin_token)
    
    if not SESSION_ID:
        print("Error: No SESSION_ID configured. Use --create-session or set SESSION_ID in .env")
        sys.exit(1)
        
    if not DEVICE_TOKEN:
        print("Error: No DEVICE_TOKEN configured. Please set DEVICE_TOKEN in .env")
        sys.exit(1)

    fetch_zones_for_session(SESSION_ID, admin_token=args.admin_token)

    ser = None
    if not args.dry_run:
        print(f"Connecting to Bridge ESP32 on {SERIAL_PORT}...")
        try:
            ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            time.sleep(2)
            print("Connected.")
        except serial.SerialException as e:
            print(f"\n[CRITICAL ERROR] Could not open Serial Port {SERIAL_PORT}")
            print("Make sure the ESP32 is plugged in and the port is correct.")
            print("If you just want to test backend posting, run with --dry-run\n")
            sys.exit(1)
    else:
        print("[Dry Run] Skipping Serial connection.")

    print("Starting virtual lap simulation.\n")
    for lap in range(1, NUM_LAPS + 1):
        run_lap(ser, SESSION_ID, lap)

    print("\nSimulation complete. Check the Coach/Driver dashboard for stored results.")
    if ser:
        ser.close()

if __name__ == "__main__":
    main()
