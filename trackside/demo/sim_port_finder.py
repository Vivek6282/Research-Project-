"""
Trackside Virtual Lap Simulator — Bridge Port Finder.
Finds the Bridge ESP32 whatever COM number Windows gave it. Each candidate port is opened,
the board is reset the standard ESP32 way, and its startup banner says what it is:
"TRACKSIDE BRIDGE" (the bridge) or "TRACKSIDE GLOVE" (the glove, which ignores USB).
Nothing is ever written to a port.
"""

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    import serial
    from serial.tools import list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

PER_PORT_LIMIT_S = 4.5      # one port can never hold the search longer than this
READ_WINDOW_S = 3.5         # how long we listen for the banner after the reset
OPEN_TIMEOUT_S = 0.2        # read timeout of an opened port
RESET_PULSE_S = 0.1         # how long the reset line is held
PREFERRED_USB_IDS = ("10C4:EA60", "1A86:7523")   # the USB-serial chips on ESP32 boards
CANDIDATES_ENV = "TRACKSIDE_PORT_CANDIDATES"     # comma-separated names; replaces discovery
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_bridge_port")
BUSY_HINT = "close the Arduino Serial Monitor"


@dataclass
class FindResult:
    """port is the bridge's port name (or None); found has one dict per port that was probed."""

    port: Optional[str] = None
    found: List[Dict[str, str]] = field(default_factory=list)


def is_auto(configured: Optional[str]) -> bool:
    """True when no specific port is configured (empty, unset or "auto")."""
    return not configured or not configured.strip() or configured.strip().lower() == "auto"


def blank_info(name: str) -> Dict[str, str]:
    """Port facts for a name that the system did not list."""
    return {"port": name, "description": "", "vid_pid": "", "serial_number": ""}


def system_ports() -> List[Dict[str, str]]:
    """Every serial port the system lists, or only the names in TRACKSIDE_PORT_CANDIDATES when that is set."""
    listed = {}
    if HAS_SERIAL:
        try:
            system_list = list(list_ports.comports())
        except Exception:
            system_list = []
        for item in system_list:
            vid_pid = f"{item.vid:04X}:{item.pid:04X}" if item.vid is not None and item.pid is not None else ""
            listed[item.device.lower()] = {
                "port": item.device, "description": item.description or "",
                "vid_pid": vid_pid, "serial_number": item.serial_number or "",
            }
    names = [n.strip() for n in os.environ.get(CANDIDATES_ENV, "").split(",") if n.strip()]
    if names:
        return [listed.get(n.lower(), blank_info(n)) for n in names]
    return list(listed.values())


def read_cached_port() -> str:
    """The last good bridge port name (only a hint, always verified), or an empty text."""
    try:
        with open(CACHE_FILE, encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def remember_port(port: str) -> None:
    """Save the port that was just verified as the bridge (a failure to save is ignored)."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as handle:
            handle.write(port + "\n")
    except OSError:
        pass


def is_bluetooth(info: Dict[str, str]) -> bool:
    """True for a Bluetooth serial port (these never hold the bridge and can hang on open)."""
    return "bluetooth" in info["description"].lower()


def order_candidates(configured: Optional[str], cached: str, ports: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Probe order: configured port, last good port, USB boards (known chips first), then the rest. No Bluetooth."""
    by_name = {p["port"].lower(): p for p in ports}
    ordered: List[Dict[str, str]] = []
    seen = set()

    def add(info):
        if info["port"].lower() not in seen:
            seen.add(info["port"].lower())
            ordered.append(info)

    if not is_auto(configured):
        add(by_name.get(configured.strip().lower(), blank_info(configured.strip())))
    if cached and cached.lower() in by_name:
        add(by_name[cached.lower()])
    known = [p for p in ports if p["vid_pid"] in PREFERRED_USB_IDS]
    other_usb = [p for p in ports if p["vid_pid"] and p["vid_pid"] not in PREFERRED_USB_IDS]
    rest = [p for p in ports if not p["vid_pid"]]
    for info in known + other_usb + rest:
        if not is_bluetooth(info):
            add(info)
    return ordered


def is_busy_error(error: Exception) -> bool:
    """True when opening failed because the port is in use or access was refused."""
    text = str(error).lower()
    return isinstance(error, PermissionError) or any(
        word in text for word in ("access is denied", "permission", "busy", "in use", "errno 13", "errno 16"))


def read_banner(connection, deadline: float, cancel: threading.Event):
    """Read lines until a Trackside banner, the deadline or a cancel; returns (verdict, detail)."""
    buffer = b""
    while time.monotonic() < deadline and not cancel.is_set():
        buffer += connection.read(max(1, connection.in_waiting))
        *lines, buffer = buffer.split(b"\n")
        for raw in lines:
            line = raw.decode("utf-8", errors="ignore").upper()
            if "TRACKSIDE BRIDGE" in line:
                return "bridge", "bridge banner received"
            if "TRACKSIDE GLOVE" in line:
                return "glove", "this is the glove, not the bridge"
    return "unknown", "no Trackside banner after the reset"


def probe_once(port: str, baud: int, deadline: float, cancel: threading.Event):
    """Open the port, reset the board, listen for its banner, always close. Returns (verdict, detail)."""
    connection = None
    try:
        connection = serial.Serial(port, baud, timeout=OPEN_TIMEOUT_S)
        if cancel.is_set():
            return "error", "probe cancelled"
        connection.dtr = False           # the standard ESP32 hard reset
        connection.rts = True
        time.sleep(RESET_PULSE_S)
        connection.rts = False
        return read_banner(connection, min(deadline, time.monotonic() + READ_WINDOW_S), cancel)
    except Exception as error:
        if is_busy_error(error):
            return "busy", BUSY_HINT
        return "error", str(error)[:120]
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def probe_port(port: str, baud: int, limit: float = PER_PORT_LIMIT_S):
    """Probe one port in a worker thread so a port that hangs on open can never block the caller."""
    outcome: Dict[str, tuple] = {}
    cancel = threading.Event()
    deadline = time.monotonic() + limit

    def work():
        outcome["result"] = probe_once(port, baud, deadline, cancel)

    worker = threading.Thread(target=work, daemon=True, name=f"probe-{port}")
    worker.start()
    worker.join(limit + 0.3)
    if worker.is_alive():
        cancel.set()
        return "error", f"no answer within {limit:.1f} s (the port hung)"
    return outcome.get("result", ("error", "probe failed"))


def report_for(info: Dict[str, str], verdict: str, detail: str) -> Dict[str, str]:
    """One result row: the port facts plus the verdict and its detail."""
    return {**info, "verdict": verdict, "detail": detail}


def find_bridge_port(configured: Optional[str], baud: int, total_timeout: float = 20.0) -> FindResult:
    """Probe the candidates one at a time and stop at the first bridge or when total_timeout is used up."""
    result = FindResult()
    if not HAS_SERIAL:
        return result
    started = time.monotonic()
    for info in order_candidates(configured, read_cached_port(), system_ports()):
        remaining = total_timeout - (time.monotonic() - started)
        if remaining <= 0:
            break
        verdict, detail = probe_port(info["port"], baud, min(PER_PORT_LIMIT_S, remaining))
        result.found.append(report_for(info, verdict, detail))
        if verdict == "bridge":
            result.port = info["port"]
            remember_port(info["port"])
            break
    return result


def probe_all_ports(baud: int) -> List[Dict[str, str]]:
    """A verdict for every serial port (probed side by side); Bluetooth ports are listed but not opened."""
    infos = system_ports()
    rows: List[Optional[Dict[str, str]]] = [None] * len(infos)

    def work(index, info):
        if is_bluetooth(info):
            rows[index] = report_for(info, "unknown", "Bluetooth port, not probed")
        else:
            rows[index] = report_for(info, *probe_port(info["port"], baud))

    workers = [threading.Thread(target=work, args=(i, info), daemon=True) for i, info in enumerate(infos)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(PER_PORT_LIMIT_S + 1.0)
    return [row if row else report_for(info, "error", "probe did not finish") for row, info in zip(rows, infos)]
