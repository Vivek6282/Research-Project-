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

from sim_port_finder import find_bridge_port, is_auto, probe_all_ports


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


def open_bridge(port_name, baud_rate):
    """Open the verified bridge port for the run (waits 2 s for the board); None with the usual warning on failure."""
    try:
        serial_connection = serial.Serial(port_name, baud_rate, timeout=1)
        time.sleep(2)
        print(f"  [OK] Connected to Bridge ESP32 on {port_name}.")
        return serial_connection
    except Exception as exc:
        print(f"  [!] Warning: Bridge ESP32 not detected on {port_name} ({exc}).")
        print("      Continuing simulation with WebSocket broadcaster and backend ingestion.\n")
        return None


def verdict_of(found, port_name):
    """The verdict the finder gave a port name (ignoring case), or "unknown" when it was not probed."""
    return next((row["verdict"] for row in found if row["port"].lower() == port_name.lower()), "unknown")


def connect_serial_bridge(port_name, baud_rate):
    """
    Finds and opens the Bridge ESP32. The configured port is verified first (by the board's
    startup banner); with SERIAL_PORT empty or "auto", or when the configured port is the glove,
    busy or silent, the other serial ports are searched.
    Input: port_name (str), baud_rate (int).
    Output: serial.Serial object on success, or None on failure.
    """
    if not HAS_SERIAL:
        print("  [!] 'pyserial' not installed. Continuing in Serial-free mode.")
        return None

    configured = (port_name or "").strip()
    if is_auto(configured):
        print("Looking for the bridge board on the serial ports (SERIAL_PORT=auto)...")
    else:
        print(f"Connecting to Bridge ESP32 on {configured}...")

    result = find_bridge_port(configured, baud_rate)
    if result.port is None:
        reason = "no serial ports found" if not result.found else "no port answered as the bridge"
        print(f"  [!] Warning: Bridge ESP32 not detected on {configured or 'auto'} ({reason}).")
        for row in result.found:
            print(f"      {row['port']}: {row['verdict']} - {row['detail']}")
        print("      Continuing simulation with WebSocket broadcaster and backend ingestion.\n")
        return None

    if not is_auto(configured) and result.port.lower() != configured.lower():
        print(f"  [i] {configured} is the {verdict_of(result.found, configured)}; "
              f"the bridge was found on {result.port}. Using {result.port}.")
    return open_bridge(result.port, baud_rate)


def list_ports_and_exit(baud_rate):
    """Print a table of every serial port (name, description, VID:PID, serial number, verdict), then exit with code 0."""
    if not HAS_SERIAL:
        print("  [!] 'pyserial' not installed. Run: pip install pyserial")
        raise SystemExit(0)
    rows = probe_all_ports(baud_rate)
    if not rows:
        print("No serial ports found.")
        raise SystemExit(0)
    headers = ("PORT", "DESCRIPTION", "VID:PID", "SERIAL NUMBER", "VERDICT")
    cells = [(r["port"], r["description"] or "-", r["vid_pid"] or "-", r["serial_number"] or "-", r["verdict"]) for r in rows]
    widths = [max(len(str(line[i])) for line in [headers] + cells) for i in range(len(headers))]
    for line in [headers] + cells:
        print("  ".join(str(value).ljust(widths[i]) for i, value in enumerate(line)).rstrip())
    print()
    for r in rows:
        print(f"{r['port']}: {r['verdict']} - {r['detail']}")
    raise SystemExit(0)
