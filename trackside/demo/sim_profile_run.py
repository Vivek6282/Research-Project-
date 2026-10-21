"""
Trackside Virtual Lap Simulator — Lap runner for a custom track profile.
Sends each simulated reading to exactly the same three places as the built-in
track does: the visualizer WebSocket, the bridge ESP32 over serial (g,STAGE),
and the backend REST API.
"""

import time

from sim_backend_poster import send_to_backend
from sim_physics import ProfileSimulator
from sim_serial_bridge import send_to_bridge
from sim_websocket_server import broadcast_reading

# The visualizer draws at most this many outline points
MAX_OUTLINE_POINTS_SENT = 2000


def run_profile_lap(simulator: ProfileSimulator, serial_connection, session_id, lap_number, total_laps, reading_delay):
    """Run one lap and print a one-line summary per corner (its peak g and worst stage)."""
    print(f"\n===== LAP {lap_number}{f' / {total_laps}' if total_laps > 0 else ''} =====")
    peaks = {}
    for packet in simulator.lap_packets(lap_number):
        broadcast_reading(packet)
        send_to_bridge(serial_connection, packet["g_force"], packet["stage"])
        send_to_backend(session_id, packet["g_force"], packet["zone"], packet["stage"], packet["speed_kmh"], lap_number=lap_number)
        if packet["zone"] != "Straight":
            best = peaks.get(packet["zone"])
            if best is None or packet["g_force"] > best[0]:
                peaks[packet["zone"]] = (packet["g_force"], packet["stage"])
        time.sleep(reading_delay)
    for label, (peak_g, stage) in peaks.items():
        print(f"  -> {label:10s} | peak {peak_g:.2f}g | {stage}")


def build_run_start_extras(simulator: ProfileSimulator) -> dict:
    """Outline (at most 2,000 points) and corner labels to add to the run_start message."""
    profile = simulator.profile
    stride = max(1, -(-len(profile.outline) // MAX_OUTLINE_POINTS_SENT))
    corners = []
    for corner in profile.corners:
        middle = (corner.start_index + (((corner.end_index - corner.start_index) % len(profile.outline)) // 2)) % len(profile.outline)
        corners.append({
            "label": corner.label,
            "start_index": corner.start_index // stride,
            "end_index": corner.end_index // stride,
            "label_index": middle // stride,
        })
    return {
        "track_name": profile.name,
        "outline": [[round(x, 1), round(y, 1)] for x, y in profile.outline[::stride]],
        "corners": corners,
    }
