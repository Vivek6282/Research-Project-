"""
Trackside — Demo Control Simulator Process Manager.

Manages the lifecycle of the virtual lap simulator child process:
- Threadsafe state behind a threading.Lock
- Background reader thread merging stderr into stdout (utf-8, errors="replace") into deque(maxlen=200)
- Child env: PYTHONUNBUFFERED=1, PYTHONIOENCODING=utf-8
- Windows: CREATE_NEW_PROCESS_GROUP
- Clean shutdown: terminate(), wait 3s, then kill()
- atexit registration
- Status JSON with friendly error parsing, bridge connectivity and port detection
"""

import os
import sys
import re
import atexit
import subprocess
import threading
import collections
from datetime import datetime, timezone
from django.conf import settings


class AlreadyRunningError(Exception):
    """Raised when start is called while a simulator process is already running."""
    pass


_lock = threading.Lock()
_process = None
_mode = None
_laps = None
_started_at = None
_output_lines = collections.deque(maxlen=200)
_reader_thread = None
_exit_code = None
_stopped_by_user = False


def is_demo_tools_enabled():
    """Returns True if DEMO_TOOLS_ENABLED environment variable is explicitly set to true."""
    val = os.getenv("DEMO_TOOLS_ENABLED", "false")
    return val.strip().lower() in ("true", "1", "yes")


def is_production_environment():
    """Returns True if DJANGO_ENV is production."""
    val = os.getenv("DJANGO_ENV", getattr(settings, "DJANGO_ENV", "production"))
    return val.strip().lower() == "production"


def _reader_loop(proc):
    """Background worker reading child stdout/stderr into output_lines deque."""
    try:
        for raw_line in iter(proc.stdout.readline, b""):
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            with _lock:
                _output_lines.append(line)
    except Exception:
        pass
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass


def start_simulator(mode, laps=None):
    """
    Starts the virtual lap simulator child process.
    Raises AlreadyRunningError if already active.
    """
    global _process, _mode, _laps, _started_at, _stopped_by_user, _exit_code, _reader_thread
    with _lock:
        if _process is not None and _process.poll() is None:
            raise AlreadyRunningError("Simulator is already running.")

        python_bin = os.getenv("DEMO_PYTHON")
        if not python_bin or not python_bin.strip():
            python_bin = sys.executable

        simulator_path = os.path.abspath(
            os.path.join(settings.BASE_DIR.parent, "demo", "virtual_lap_simulator.py")
        )
        demo_dir = os.path.dirname(simulator_path)

        cmd = [python_bin, "-u", simulator_path]
        if mode == "continuous":
            cmd.append("--continuous")
        elif mode == "laps":
            cmd.extend(["--laps", str(laps)])
        else:
            raise ValueError(f"Invalid mode: {mode}")

        child_env = os.environ.copy()
        child_env["PYTHONUNBUFFERED"] = "1"
        child_env["PYTHONIOENCODING"] = "utf-8"

        creation_flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

        _output_lines.clear()
        _mode = mode
        _laps = laps
        _started_at = datetime.now(timezone.utc).isoformat()
        _stopped_by_user = False
        _exit_code = None

        _process = subprocess.Popen(
            cmd,
            shell=False,
            cwd=demo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=child_env,
            creationflags=creation_flags,
        )

        _reader_thread = threading.Thread(
            target=_reader_loop,
            args=(_process,),
            daemon=True,
            name="SimulatorOutputReader",
        )
        _reader_thread.start()

        return _process.pid


def stop_simulator():
    """
    Idempotent stop for the simulator process.
    Stop = terminate(), wait 3 s, then kill().
    """
    global _process, _stopped_by_user, _exit_code
    with _lock:
        proc = _process
        if proc is None:
            return False
        if proc.poll() is not None:
            _exit_code = proc.poll()
            return False

        _stopped_by_user = True

    try:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2.0)
            except Exception:
                pass
    except Exception:
        pass

    with _lock:
        _exit_code = proc.poll()

    return True


def parse_friendly_error(exit_code, lines, stopped_by_user=False):
    """
    Derives user-friendly error text from child process exit code and output logs.
    """
    text = "\n".join(lines)
    text_lower = text.lower()

    # 1. ModuleNotFoundError
    for line in lines:
        if "ModuleNotFoundError" in line:
            m = re.search(r"No module named ['\"]?([a-zA-Z0-9_\-]+)['\"]?", line)
            pkg = m.group(1) if m else "package"
            return f"Missing Python package: {pkg}. Run: pip install -r trackside/demo/requirements.txt"

    # 2. Port already in use
    if (
        "address already in use" in text_lower
        or "errno 10048" in text_lower
        or "errno 98" in text_lower
        or "10048" in text_lower
    ):
        return "Another simulator is already running (port 8765 is in use). Close it and try again."

    # 3. COM port busy / PermissionError
    if (
        "access is denied" in text_lower
        or ("permissionerror" in text_lower and ("com" in text_lower or "port" in text_lower or "serial" in text_lower))
    ):
        if exit_code is not None and exit_code != 0 and not stopped_by_user:
            return "The COM port is busy. Close the Arduino Serial Monitor."

    # 4. Any other non-zero exit
    if exit_code is not None and exit_code != 0 and not stopped_by_user:
        return f"The simulator stopped with an error (exit code {exit_code})."

    return None


def get_simulator_status():
    """
    Builds the status dictionary reflecting the current simulator process state.
    """
    with _lock:
        proc = _process
        lines = list(_output_lines)
        mode = _mode
        laps = _laps
        started_at = _started_at
        stopped = _stopped_by_user
        current_exit = _exit_code

    if proc is not None:
        poll_result = proc.poll()
        if poll_result is not None:
            running = False
            exit_code = poll_result
        else:
            running = True
            exit_code = None
    else:
        running = False
        exit_code = current_exit

    # Bridge ESP32 connected detection
    bridge_connected = None
    for line in reversed(lines):
        if "Connected to Bridge ESP32" in line:
            bridge_connected = True
            break
        elif "Bridge ESP32 not detected" in line:
            bridge_connected = False
            break

    # Port hint extraction (COMx or /dev/...)
    port_hint = None
    for line in reversed(lines):
        if "Bridge ESP32" in line:
            m = re.search(r"\bon\s+([A-Za-z0-9_/\\.-]+)", line, re.IGNORECASE)
            if m:
                port_hint = m.group(1).rstrip(".(),")
                break
            m2 = re.search(r"\b(COM\d+|/dev/[A-Za-z0-9_\-\.]+)\b", line, re.IGNORECASE)
            if m2:
                port_hint = m2.group(1).rstrip(".(),")
                break

    error = parse_friendly_error(exit_code, lines, stopped_by_user=stopped)

    return {
        "enabled": is_demo_tools_enabled(),
        "running": running,
        "pid": proc.pid if (proc and running) else None,
        "mode": mode,
        "laps": laps,
        "started_at": started_at,
        "exit_code": exit_code,
        "bridge_connected": bridge_connected,
        "port_hint": port_hint,
        "last_lines": lines[-15:],
        "error": error,
    }


def reset_state_for_testing():
    """Test helper to cleanly reset all module state."""
    global _process, _mode, _laps, _started_at, _exit_code, _stopped_by_user
    stop_simulator()
    with _lock:
        _process = None
        _mode = None
        _laps = None
        _started_at = None
        _exit_code = None
        _stopped_by_user = False
        _output_lines.clear()


# Automatically stop child process when parent python process exits
atexit.register(stop_simulator)
