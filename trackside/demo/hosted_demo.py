"""
Trackside — hosted demo helper (glove demo with a hosted site).

1. On the site: Coach > Maps & Demo > Connect laptop > Start link, then press "Copy lines".
2. Here:        py hosted_demo.py
It reads the four copied lines from the clipboard, writes them into demo/.env (nothing else in that file
changes), then starts the simulator (default: --post-batch 4 --laps 5). The token is never printed.

Other options:  py hosted_demo.py --from-file lines.txt   (read the lines from a file instead of the clipboard)
                py hosted_demo.py --write-only             (update .env, do not start the simulator)
Any other arguments are passed to the simulator, for example:  py hosted_demo.py --laps 3
"""

import json
import os
import subprocess
import sys

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(DEMO_DIR, ".env")
KEYS = ("BACKEND_URL", "SESSION_ID", "DEVICE_TOKEN", "DEMO_ZONES")
# 4 readings per request: over the internet one request per reading cannot keep up with 5 readings a second
DEFAULT_SIM_ARGS = ["--post-batch", "4", "--laps", "5"]


def read_clipboard() -> str:
    """The clipboard text (Windows PowerShell, macOS pbpaste or Linux xclip); exits with a hint when it cannot be read."""
    commands = [["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"], ["pbpaste"], ["xclip", "-selection", "clipboard", "-o"]]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    sys.exit("Could not read the clipboard. Press 'Copy lines' on the site first, or use --from-file lines.txt")


def parse_lines(text: str) -> dict:
    """The four KEY=value pairs from the copied text; exits with a clear message when one is missing or wrong."""
    found = {}
    for line in text.splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key in KEYS:
            found[key] = value.strip()
    missing = [key for key in KEYS if not found.get(key)]
    if missing:
        sys.exit(f"The copied text is missing: {', '.join(missing)}. On the site, press Start link, then 'Copy lines', then run this again.")
    if "•" in found["DEVICE_TOKEN"] or not found["DEVICE_TOKEN"].startswith("dt_"):
        sys.exit("The token on the clipboard is hidden. Press 'Copy lines' (not just select the text) and run this again.")
    if not found["BACKEND_URL"].startswith(("http://", "https://")):
        sys.exit("BACKEND_URL must start with http:// or https://")
    try:
        if not isinstance(json.loads(found["DEMO_ZONES"]), dict):
            raise ValueError
    except ValueError:
        sys.exit("DEMO_ZONES is not valid. Press Start link and 'Copy lines' again.")
    return found


def update_env(values: dict) -> None:
    """Set the four keys in demo/.env, keeping every other line (and creating the file when it is missing)."""
    lines = []
    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    remaining = dict(values)
    result = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in remaining and "=" in line and not line.lstrip().startswith("#"):
            result.append(f"{key}={remaining.pop(key)}")
        else:
            result.append(line)
    result.extend(f"{key}={value}" for key, value in remaining.items())
    with open(ENV_FILE, "w", encoding="utf-8") as handle:
        handle.write("\n".join(result) + "\n")


def main() -> None:
    """Read the lines, update .env and start the simulator."""
    args = sys.argv[1:]
    write_only = "--write-only" in args
    source_file = None
    if "--from-file" in args:
        index = args.index("--from-file")
        source_file = args[index + 1] if index + 1 < len(args) else sys.exit("--from-file needs a file name")
        args = args[:index] + args[index + 2:]
    args = [a for a in args if a != "--write-only"]

    if source_file:
        with open(source_file, encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = read_clipboard()
    values = parse_lines(text)
    update_env(values)
    print(f"Updated {ENV_FILE}")
    print(f"  Site:    {values['BACKEND_URL']}")
    print(f"  Session: {values['SESSION_ID']}")
    print("  Token:   saved (not shown)")
    if write_only:
        return
    command = [sys.executable, os.path.join(DEMO_DIR, "virtual_lap_simulator.py")] + (args or DEFAULT_SIM_ARGS)
    print("Starting the simulator: " + " ".join(command[1:]) + "\n")
    raise SystemExit(subprocess.call(command, cwd=DEMO_DIR))


if __name__ == "__main__":
    main()
