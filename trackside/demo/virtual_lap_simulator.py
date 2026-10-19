"""
Trackside — Virtual Lap Simulator (Main Entry Point).
Orchestrates simulated kart driving telemetry around a virtual track:
broadcasting over local WebSocket, streaming to Bridge ESP32 serial, and
asynchronously ingesting telemetry batches into the Django backend.
"""

import argparse
import random
import sys
import time

from sim_config import (
    BACKEND_URL,
    DEVICE_TOKEN,
    NUM_LAPS,
    READING_DELAY_SECONDS,
    SERIAL_BAUD,
    SERIAL_PORT,
    SESSION_ID,
    WS_HOST,
    WS_PORT,
    DEMO_ZONES_RAW,
    validate_demo_zones,
)
from sim_track import (
    TRACK,
    classify_stage,
    create_session,
    fetch_zones_for_session,
    generate_speed,
    generate_turn_readings,
)
from sim_backend_poster import (
    flush_backend_telemetry,
    send_to_backend,
    start_backend_worker,
)
from sim_websocket_server import (
    broadcast_reading,
    start_websocket_server,
)
from sim_serial_bridge import (
    connect_serial_bridge,
    send_to_bridge,
)


def run_lap(serial_connection, session_id, lap_number, total_laps, reading_delay):
    """
    Executes one simulated lap around the virtual track.
    Computes track progress (0.0 to 1.0) and synchronizes readings across
    WebSocket broadcast, serial bridge, and backend REST ingestion.
    Input: serial_connection (serial.Serial or None), session_id (str), lap_number (int),
           total_laps (int), reading_delay (float).
    Output: None.
    """
    lap_header = f"\n===== LAP {lap_number}{f' / {total_laps}' if total_laps > 0 else ''} ====="
    print(lap_header)
    total_readings_in_lap = sum(turn["readings"] for turn in TRACK)
    current_reading_index = 0

    for turn in TRACK:
        driver_aggression = random.choices([0.85, 1.0, 1.35], weights=[0.4, 0.4, 0.2])[0]
        turn_readings = generate_turn_readings(turn, driver_aggression)
        peak_g = max(turn_readings)
        peak_stage = classify_stage(peak_g, turn["threshold"])
        print(f"  -> {turn['name']:10s} | peak {peak_g:.2f}g | {peak_stage}")

        for measured_g in turn_readings:
            current_stage = classify_stage(measured_g, turn["threshold"])
            derived_speed_kmh = generate_speed(turn["name"], measured_g)

            normalized_track_progress = round(current_reading_index / max(1, total_readings_in_lap), 4)
            current_reading_index += 1

            telemetry_packet = {
                "lap": lap_number,
                "zone": turn["name"],
                "g_force": measured_g,
                "stage": current_stage,
                "speed_kmh": derived_speed_kmh,
                "track_progress": normalized_track_progress,
                "threshold": turn["threshold"],
            }

            # 1. Local WebSocket broadcast to visualizer
            broadcast_reading(telemetry_packet)

            # 2. Output to physical Bridge ESP32 via serial
            send_to_bridge(serial_connection, measured_g, current_stage)

            # 3. Post to backend REST API
            send_to_backend(session_id, measured_g, turn["name"], current_stage, derived_speed_kmh, lap_number=lap_number)

            time.sleep(reading_delay)


def parse_and_validate_limits(raw_limit_arguments):
    """
    Parses and validates --limit command-line arguments.
    Input: raw_limit_arguments (list of strings e.g. ['Hairpin=1.05']).
    Output: Dictionary mapping canonical corner names to validated float limits.
    """
    canonical_corner_names = {"hairpin": "Hairpin", "sweeper": "Sweeper", "chicane": "Chicane"}
    validated_custom_limits = {}

    for item in raw_limit_arguments:
        if "=" not in item:
            print(f"Error: Invalid --limit format '{item}'. Expected NAME=VALUE.")
            sys.exit(2)
        corner_raw, value_raw = item.split("=", 1)
        canonical_name = canonical_corner_names.get(corner_raw.strip().lower())
        if not canonical_name:
            print(f"Error: Unknown corner name '{corner_raw.strip()}' in --limit. Allowed corners: Hairpin, Sweeper, Chicane.")
            sys.exit(2)
        try:
            parsed_limit = float(value_raw.strip())
        except ValueError:
            print(f"Error: Invalid limit value '{value_raw.strip()}' for '{corner_raw.strip()}'. Must be a float.")
            sys.exit(2)
        if parsed_limit < 0.50 or parsed_limit > 2.50:
            print(f"Error: Limit value {parsed_limit:.2f} for '{corner_raw.strip()}' out of range. Must be between 0.50 and 2.50.")
            sys.exit(2)
        validated_custom_limits[canonical_name] = parsed_limit

    return validated_custom_limits


def main():
    """
    CLI entry point initializing options, WebSocket server, serial bridge,
    and running the lap simulation loop.
    """
    cli_parser = argparse.ArgumentParser(description="Trackside Virtual Lap Simulator with Live WebSocket Telemetry")
    cli_parser.add_argument("--create-session", action="store_true", help="Automatically create a new session before running")
    cli_parser.add_argument("--admin-token", type=str, help="Admin or Coach JWT Token for creating sessions")
    cli_parser.add_argument("--dry-run", action="store_true", help="Skip connecting to Serial Port entirely")
    cli_parser.add_argument("--laps", type=int, default=NUM_LAPS, help=f"Number of laps to run (default: {NUM_LAPS}, 0 for continuous)")
    cli_parser.add_argument("--continuous", action="store_true", help="Run laps continuously until stopped with Ctrl+C")
    cli_parser.add_argument("--delay", type=float, default=READING_DELAY_SECONDS, help=f"Delay between readings in seconds (default: {READING_DELAY_SECONDS})")
    cli_parser.add_argument("--ws-port", type=int, default=WS_PORT, help=f"Port for local WebSocket telemetry broadcaster (default: {WS_PORT})")
    cli_parser.add_argument("--ws-host", type=str, default=WS_HOST, help=f"Host for local WebSocket telemetry broadcaster (default: {WS_HOST})")
    cli_parser.add_argument("--limit", action="append", default=[], help="Custom corner limit, e.g. --limit Hairpin=1.00 (repeatable)")
    cli_args = cli_parser.parse_args()

    custom_corner_limits = parse_and_validate_limits(cli_args.limit)
    corner_sources = {"Hairpin": "default", "Sweeper": "default", "Chicane": "default"}

    active_session_id = SESSION_ID
    if cli_args.create_session:
        if not cli_args.admin_token:
            print("Error: --create-session requires --admin-token to authenticate.")
            sys.exit(1)
        active_session_id = create_session(cli_args.admin_token)

    validate_demo_zones(DEMO_ZONES_RAW, active_session_id)

    if not active_session_id:
        print("  [i] Notice: No SESSION_ID configured.")
        print("      Telemetry will not be stored in backend, but will broadcast over WebSocket and Serial.")
    if not DEVICE_TOKEN:
        print("  [i] Notice: No DEVICE_TOKEN configured. Backend POSTs will be skipped.")

    fetch_zones_for_session(
        active_session_id,
        admin_token=cli_args.admin_token,
        custom_limits=custom_corner_limits,
        corner_sources=corner_sources,
    )

    # Precedence: --limit (custom) beats backend zone beats default
    for corner_name, custom_limit_value in custom_corner_limits.items():
        for turn in TRACK:
            if turn["name"] == corner_name:
                turn["threshold"] = custom_limit_value
                corner_sources[corner_name] = "custom"

    print("\nCorner limits in force:")
    for corner_name in ["Hairpin", "Sweeper", "Chicane"]:
        active_threshold = next(turn["threshold"] for turn in TRACK if turn["name"] == corner_name)
        source_label = corner_sources[corner_name]
        print(f"{corner_name} limit {active_threshold:.2f} g ({source_label})")

    if active_session_id and DEVICE_TOKEN:
        start_backend_worker(active_session_id, DEVICE_TOKEN, BACKEND_URL)

    print("\nStarting local WebSocket telemetry broadcaster...")
    ws_thread = start_websocket_server(host=cli_args.ws_host, port=cli_args.ws_port)
    if ws_thread:
        print("  [i] Open the visualizer: Coach Settings > Open Live Demo Visualizer, or frontend/public/demo/track_visualization.html")

    serial_connection = None
    if not cli_args.dry_run:
        serial_connection = connect_serial_bridge(SERIAL_PORT, SERIAL_BAUD)
    else:
        print("  [Dry Run] Skipping Serial connection.")

    target_lap_count = 0 if cli_args.continuous else cli_args.laps
    current_lap = 1
    print("\n" + "=" * 60)
    print(" TRACKSIDE VIRTUAL LAP SIMULATOR -- RUNNING")
    print(f" Target Laps: {'Infinite (Continuous)' if target_lap_count == 0 else target_lap_count}")
    print(f" Reading Interval: {cli_args.delay}s")
    print(f" WebSocket Endpoint: ws://{cli_args.ws_host}:{cli_args.ws_port}")
    print("=" * 60 + "\n")

    try:
        while True:
            run_lap(serial_connection, active_session_id, current_lap, target_lap_count, cli_args.delay)
            current_lap += 1
            if target_lap_count > 0 and current_lap > target_lap_count:
                break
    except KeyboardInterrupt:
        print("\n[!] Simulation halted by user.")
    finally:
        if serial_connection:
            try:
                serial_connection.close()
            except Exception:
                pass
        flush_backend_telemetry(timeout_seconds=5.0)
        print("\nSimulation session finished.")
        print("Check 'track_visualization.html' and Coach/Driver dashboards for results.")


if __name__ == "__main__":
    main()
