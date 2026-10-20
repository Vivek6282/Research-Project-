"""
Trackside Shared Protocol Synchronization Tool
Synchronizes firmware/shared/trackside_radio_protocol.h into each Arduino sketch directory.
Supports --check flag to detect drift and enforce continuous synchronization in test pipelines.
"""

import os
import shutil
import sys


def get_sync_paths():
    """
    Computes absolute file paths for source protocol header and sketch destinations.
    Input: None.
    Output: Tuple of (source_path, list of destination_paths).
    """
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    firmware_dir = os.path.dirname(tools_dir)

    source_path = os.path.join(firmware_dir, "shared", "trackside_radio_protocol.h")
    destination_dirs = [
        os.path.join(firmware_dir, "trackside_bridge"),
        os.path.join(firmware_dir, "trackside_glove"),
        os.path.join(firmware_dir, "trackside_glove_usb"),
    ]
    destination_paths = [
        os.path.join(dest_dir, "trackside_radio_protocol.h")
        for dest_dir in destination_dirs
    ]
    return source_path, destination_paths


def check_sync():
    """
    Verifies that all sketch copies match the master shared header exactly.
    Input: None.
    Output: Exits with 0 if in sync, exits with 1 if missing or drifted.
    """
    source_path, destination_paths = get_sync_paths()
    if not os.path.isfile(source_path):
        print(f"Error: Master header not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    with open(source_path, "rb") as sf:
        master_bytes = sf.read()

    drift_detected = False
    for dest_path in destination_paths:
        if not os.path.isfile(dest_path):
            print(f"Drift detected: Missing copy at {dest_path}", file=sys.stderr)
            drift_detected = True
            continue
        with open(dest_path, "rb") as df:
            dest_bytes = df.read()
        if master_bytes != dest_bytes:
            print(f"Drift detected: Out of sync copy at {dest_path}", file=sys.stderr)
            drift_detected = True

    if drift_detected:
        print("Error: Firmware protocol copies differ from shared source. Run 'python sync_shared.py' to update.", file=sys.stderr)
        sys.exit(1)
    else:
        print("Success: All firmware protocol copies are in sync with shared source.")
        sys.exit(0)


def perform_sync():
    """
    Copies the master shared header to all sketch directories.
    Input: None.
    Output: Exits with 0 on success, exits with 1 on error.
    """
    source_path, destination_paths = get_sync_paths()
    if not os.path.isfile(source_path):
        print(f"Error: Master header not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    for dest_path in destination_paths:
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copyfile(source_path, dest_path)
        print(f"Synchronized -> {dest_path}")

    print("Success: Successfully synchronized trackside_radio_protocol.h to all sketch directories.")
    sys.exit(0)


def main():
    """Entry point parsing command line arguments and executing sync or check."""
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_sync()
    else:
        perform_sync()


if __name__ == "__main__":
    main()
