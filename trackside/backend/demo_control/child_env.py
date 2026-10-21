"""
Trackside Demo Control — Environment for the simulator child process.

The child gets a SMALL allow-listed environment plus the values for this run
(session id, device token, backend URL, zone map). The Django server's own
secrets (SECRET_KEY, database settings, admin passwords) are NOT passed on.
Secrets reach the child only through this environment, never on the command line.
"""

import os
from typing import Dict

# Variables the Python child needs to start and talk to the network, on Windows and Linux
ALLOWED_PARENT_VARS = (
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR",
    "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL", "VIRTUAL_ENV",
    "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
)
# The names the simulator reads for one run; they win over anything in trackside/demo/.env
RUN_VAR_NAMES = ("SESSION_ID", "DEVICE_TOKEN", "BACKEND_URL", "DEMO_ZONES")


def build_child_env(run_values: Dict[str, str]) -> Dict[str, str]:
    """Allow-listed parent variables, unbuffered UTF-8 output, and this run's values."""
    unknown = set(run_values) - set(RUN_VAR_NAMES)
    if unknown:
        raise ValueError(f"Unexpected run variables: {sorted(unknown)}")
    env = {name: os.environ[name] for name in ALLOWED_PARENT_VARS if name in os.environ}
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.update({name: str(value) for name, value in run_values.items()})
    return env
