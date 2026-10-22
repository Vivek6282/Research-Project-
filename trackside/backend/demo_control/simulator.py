"""
Trackside — Demo Control Simulator Process Manager.

Manages the lifecycle of the virtual lap simulator child process:
- Threadsafe state behind a threading.Lock
- Background reader thread merging stderr into stdout (utf-8, errors="replace") into deque(maxlen=200)
- Child env: small allow-list plus this run's values (see child_env.py)
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

from demo_control.child_env import build_child_env


class AlreadyRunningError(Exception):
    """Raised when start is called while a simulator process is already running."""
    pass


_lock = threading.Lock()
_process = None
_run_info = None
_current_lap = None
_started_at = None
_output_lines = collections.deque(maxlen=200)
_reader_thread = None
_exit_code = None
_stopped_by_user = False


def is_simulator_running():
    """Returns True if the simulator process is currently running."""
    with _lock:
        return _process is not None and _process.poll() is None


def is_demo_tools_enabled():
    """Returns True if DEMO_TOOLS_ENABLED environment variable is explicitly set to true."""
    val = os.getenv("DEMO_TOOLS_ENABLED", "false")
    return val.strip().lower() in ("true", "1", "yes")


def is_production_environment():
    """Returns True if DJANGO_ENV is production."""
    val = os.getenv("DJANGO_ENV", getattr(settings, "DJANGO_ENV", "production"))
    return val.strip().lower() == "production"


LAP_LINE = re.compile(r"===== LAP (\d+)")


def _reader_loop(proc):
    """Background worker reading child stdout/stderr into output_lines deque and tracking the lap."""
    global _current_lap
    try:
        for raw_line in iter(proc.stdout.readline, b""):
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            with _lock:
                _output_lines.append(line)
                lap_match = LAP_LINE.search(line)
                if lap_match:
                    _current_lap = int(lap_match.group(1))
    except Exception:
        pass
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass


def start_simulator(extra_args, run_values, run_info):
    """
    Starts the virtual lap simulator child process with a fixed command.
    extra_args: already-validated argument strings (for example ["--laps", "3"]).
    run_values: this run's SESSION_ID, DEVICE_TOKEN, BACKEND_URL and DEMO_ZONES (environment only).
    run_info: plain facts about the run for the status panel (no secrets).
    Raises AlreadyRunningError if already active.
    """
    global _process, _run_info, _current_lap, _started_at, _stopped_by_user, _exit_code, _reader_thread
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
        cmd = [python_bin, "-u", simulator_path] + [str(arg) for arg in extra_args]

        creation_flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

        _output_lines.clear()
        _run_info = dict(run_info)
        _current_lap = None
        _started_at = datetime.now(timezone.utc).isoformat()
        _stopped_by_user = False
        _exit_code = None

        _process = subprocess.Popen(
            cmd,
            shell=False,
            cwd=demo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=build_child_env(run_values),
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


from demo_control.parser import (
    parse_friendly_error,
    detect_bridge_connection,
    extract_port_hint,
)


def run_state(running, exit_code, stopped, has_run):
    """One word for the panel: idle, running, finished, stopped or failed."""
    if not has_run:
        return "idle"
    if running:
        return "running"
    if stopped:
        return "stopped"
    return "finished" if exit_code == 0 else "failed"


def get_simulator_status():
    """
    Builds the status dictionary reflecting the current simulator process state.
    """
    with _lock:
        proc = _process
        lines = list(_output_lines)
        run_info = dict(_run_info) if _run_info else None
        current_lap = _current_lap
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
    bridge_connected = detect_bridge_connection(lines)

    # Port hint extraction (COMx or /dev/...)
    port_hint = extract_port_hint(lines)

    error = parse_friendly_error(exit_code, lines, stopped_by_user=stopped)

    return {
        "enabled": is_demo_tools_enabled(),
        "running": running,
        "state": run_state(running, exit_code, stopped, run_info is not None),
        "pid": proc.pid if (proc and running) else None,
        "laps": run_info.get("laps") if run_info else None,
        "current_lap": current_lap,
        "started_at": started_at,
        "exit_code": exit_code,
        "bridge_connected": bridge_connected,
        "port_hint": port_hint,
        "last_lines": lines[-15:],
        "error": error,
        "limits": run_info.get("limits") if run_info else None,
        "limits_custom": run_info.get("limits_custom") if run_info else None,
        "run": run_info,
    }


def get_run_info():
    """A copy of the current run's facts (including ids needed for clean-up), or None."""
    with _lock:
        return dict(_run_info) if _run_info else None


def mark_run_finalized():
    """Remember that this run's session, device and token have been cleaned up."""
    with _lock:
        if _run_info is not None:
            _run_info["finalized"] = True


def reset_state_for_testing():
    """Test helper to cleanly reset all module state."""
    global _process, _run_info, _current_lap, _started_at, _exit_code, _stopped_by_user
    stop_simulator()
    with _lock:
        _process = None
        _run_info = None
        _current_lap = None
        _started_at = None
        _exit_code = None
        _stopped_by_user = False
        _output_lines.clear()


# Automatically stop child process when parent python process exits
atexit.register(stop_simulator)
