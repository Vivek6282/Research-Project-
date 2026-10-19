"""
Trackside Demo Control — Simulator Log and Error Parsing.
This module extracts user-friendly diagnostic messages, ESP32 bridge connectivity status,
and serial port hints from child process output streams.
"""

import re


def parse_friendly_error(exit_code, lines, stopped_by_user=False):
    """
    Derives user-friendly error text from child process exit code and output logs.
    Input: exit_code (int or None), lines (list of strings), stopped_by_user (bool).
    Output: Friendly error message string or None.
    """
    if lines is None:
        lines = []
    merged_output = "\n".join(lines)
    output_lower = merged_output.lower()

    # 1. ModuleNotFoundError
    for line in lines:
        if "ModuleNotFoundError" in line:
            matched_module = re.search(r"No module named ['\"]?([a-zA-Z0-9_\-]+)['\"]?", line)
            package_name = matched_module.group(1) if matched_module else "package"
            return f"Missing Python package: {package_name}. Run: pip install -r trackside/demo/requirements.txt"

    # 2. Port already in use
    if (
        "address already in use" in output_lower
        or "errno 10048" in output_lower
        or "errno 98" in output_lower
        or "10048" in output_lower
    ):
        return "Another simulator is already running (port 8765 is in use). Close it and try again."

    # 3. COM port busy / PermissionError
    if (
        "access is denied" in output_lower
        or ("permissionerror" in output_lower and ("com" in output_lower or "port" in output_lower or "serial" in output_lower))
    ):
        if exit_code is not None and exit_code != 0 and not stopped_by_user:
            return "The COM port is busy. Close the Arduino Serial Monitor."

    # 4. Any other non-zero exit
    if exit_code is not None and exit_code != 0 and not stopped_by_user:
        return f"The simulator stopped with an error (exit code {exit_code})."

    return None


def detect_bridge_connection(lines):
    """
    Determines if the Bridge ESP32 hardware was detected from log lines.
    Input: lines (list of strings).
    Output: True if connected, False if explicitly not detected, None if unknown.
    """
    if lines is None:
        return None
    for line in reversed(lines):
        if "Connected to Bridge ESP32" in line:
            return True
        elif "Bridge ESP32 not detected" in line:
            return False
    return None


def extract_port_hint(lines):
    """
    Extracts the serial port hint (e.g. COM5 or /dev/ttyUSB0) from log lines.
    Input: lines (list of strings).
    Output: Port string or None.
    """
    if lines is None:
        return None
    for line in reversed(lines):
        if "Bridge ESP32" in line:
            matched_port = re.search(r"\bon\s+([A-Za-z0-9_/\\.-]+)", line, re.IGNORECASE)
            if matched_port:
                return matched_port.group(1).rstrip(".(),")
            matched_com = re.search(r"\b(COM\d+|/dev/[A-Za-z0-9_\-\.]+)\b", line, re.IGNORECASE)
            if matched_com:
                return matched_com.group(1).rstrip(".(),")
    return None
