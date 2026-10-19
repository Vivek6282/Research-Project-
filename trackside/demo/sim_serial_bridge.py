"""
Trackside Virtual Lap Simulator — Serial Bridge to ESP32 Hardware.
Relays lateral g-force readings and warning stages over USB Serial to the physical glove bridge.
Provides fault-tolerant connections with graceful degradation if hardware is absent.
"""

import time

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


def send_to_bridge(serial_connection, lateral_g_force, warning_stage=None):
    """
    Transmits lateral g-force measurement and warning stage to the Bridge ESP32 via serial.
    Input: serial_connection (serial.Serial or None), lateral_g_force (float), warning_stage (str or None).
    Output: None.
    """
    if not serial_connection:
        return
    try:
        if warning_stage:
            serial_connection.write(f"{lateral_g_force},{warning_stage}\n".encode())
        else:
            serial_connection.write(f"{lateral_g_force}\n".encode())
    except Exception as exc:
        print(f"  [!] Serial send failed: {exc}")


def connect_serial_bridge(port_name, baud_rate):
    """
    Attempts to establish a serial connection to the Bridge ESP32.
    Input: port_name (str), baud_rate (int).
    Output: serial.Serial object on success, or None on failure.
    """
    if not HAS_SERIAL:
        print("  [!] 'pyserial' not installed. Continuing in Serial-free mode.")
        return None

    print(f"Connecting to Bridge ESP32 on {port_name}...")
    try:
        serial_connection = serial.Serial(port_name, baud_rate, timeout=1)
        time.sleep(2)
        print(f"  [OK] Connected to Bridge ESP32 on {port_name}.")
        return serial_connection
    except Exception as exc:
        print(f"  [!] Warning: Bridge ESP32 not detected on {port_name} ({exc}).")
        print("      Continuing simulation with WebSocket broadcaster and backend ingestion.\n")
        return None
