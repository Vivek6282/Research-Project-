"""
Trackside Virtual Lap Simulator — WebSocket Broadcaster.
Hosts a local WebSocket server to stream real-time lap telemetry directly to companion
visualizers such as frontend/public/demo/track_visualization.html.
"""

import asyncio
import json
import threading
import time

import os
from urllib.parse import urlsplit

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

from sim_config import WS_HOST, WS_PORT, WS_ALLOWED_ORIGINS, WS_ALLOW_NULL_ORIGIN
from sim_track import TRACK

CONNECTED_CLIENTS = set()
WS_LOOP = None
LATEST_RUN_START = None
RUN_START_LOCK = threading.Lock()
WS_SERVER = None
SERVER_READY = threading.Event()
ACTUAL_PORT = None


def normalize_origin(origin_str):
    """
    Normalizes origin string for case-insensitive scheme and authority matching.
    Input: origin_str (str).
    Output: normalized origin string (str).
    """
    if not origin_str or not isinstance(origin_str, str):
        return ""
    origin_stripped = origin_str.strip()
    if origin_stripped.lower() == "null":
        return "null"
    try:
        parts = urlsplit(origin_stripped)
        if not parts.scheme or not parts.netloc:
            return origin_stripped.lower()
        return f"{parts.scheme.lower()}://{parts.netloc.lower()}"
    except Exception:
        return origin_stripped.lower()


def is_origin_allowed(origin_header):
    """
    Validates WebSocket Origin header using exact equality matching.
    Allows clients without an Origin header (e.g. local tools, CLI scripts).
    Input: origin_header (str or None).
    Output: bool.
    """
    if origin_header is None:
        return True

    norm_origin = normalize_origin(origin_header)

    if norm_origin == "null":
        allow_null_env = os.getenv("WS_ALLOW_NULL_ORIGIN", "true").strip().lower() in ("true", "1", "yes")
        return allow_null_env and ("null" in [o.lower() for o in WS_ALLOWED_ORIGINS] or WS_ALLOW_NULL_ORIGIN)

    if "*" in WS_ALLOWED_ORIGINS:
        return True

    normalized_allowed = [normalize_origin(o) for o in WS_ALLOWED_ORIGINS if o.lower() != "null"]
    return norm_origin in normalized_allowed


async def _ws_handler(websocket):
    """
    Handles incoming WebSocket connections and enforces exact origin checks.
    Input: websocket connection instance.
    Output: None.
    """
    origin_header = None
    if hasattr(websocket, "request_headers"):
        origin_header = websocket.request_headers.get("Origin")
    elif hasattr(websocket, "request") and hasattr(websocket.request, "headers"):
        origin_header = websocket.request.headers.get("Origin")

    if not is_origin_allowed(origin_header):
        print(f"  [!] Rejected WebSocket connection from unauthorized origin: {origin_header}")
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    CONNECTED_CLIENTS.add(websocket)
    try:
        handshake_payload = {
            "type": "connection_ack",
            "message": "Trackside Telemetry Stream Connected",
            "zones": [turn["name"] for turn in TRACK],
            "track_length": sum(turn["readings"] for turn in TRACK),
        }
        await websocket.send(json.dumps(handshake_payload))

        replayed_start = None
        with RUN_START_LOCK:
            if LATEST_RUN_START is not None:
                replayed_start = dict(LATEST_RUN_START)
                replayed_start["replay"] = True

        if replayed_start is not None:
            await websocket.send(json.dumps(replayed_start))

        await websocket.wait_closed()
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)


async def _async_broadcast(message_json_string):
    """
    Distributes message to all currently connected WebSocket clients.
    Input: message_json_string (str).
    Output: None.
    """
    if CONNECTED_CLIENTS:
        active_clients = list(CONNECTED_CLIENTS)
        await asyncio.gather(
            *[client.send(message_json_string) for client in active_clients],
            return_exceptions=True,
        )


def broadcast_reading(telemetry_data):
    """
    Dispatches telemetry reading payload to background asyncio loop.
    Input: telemetry_data (dict).
    Output: None.
    """
    global WS_LOOP
    if "threshold" not in telemetry_data:
        for turn in TRACK:
            if turn["name"] == telemetry_data.get("zone"):
                telemetry_data["threshold"] = turn["threshold"]
                break
    if WS_LOOP and WS_LOOP.is_running():
        formatted_message = json.dumps(telemetry_data)
        asyncio.run_coroutine_threadsafe(_async_broadcast(formatted_message), WS_LOOP)


def broadcast_event(event_payload):
    """
    Dispatches non-reading event payload dictionary directly to background asyncio loop.
    Remembers run_start and clears on run_end for late-joining clients.
    Input: event_payload (dict).
    Output: None.
    """
    global WS_LOOP, LATEST_RUN_START
    if isinstance(event_payload, dict):
        event_type = event_payload.get("type")
        if event_type == "run_start":
            with RUN_START_LOCK:
                LATEST_RUN_START = dict(event_payload)
        elif event_type == "run_end":
            with RUN_START_LOCK:
                LATEST_RUN_START = None

    if WS_LOOP and WS_LOOP.is_running():
        formatted_message = json.dumps(event_payload)
        asyncio.run_coroutine_threadsafe(_async_broadcast(formatted_message), WS_LOOP)


def reset_server_state():
    """
    Resets remembered run_start payload and connected clients for test isolation.
    Output: None.
    """
    global LATEST_RUN_START
    with RUN_START_LOCK:
        LATEST_RUN_START = None


def get_actual_port():
    """
    Returns the port number the WebSocket server is currently listening on.
    Output: int or None.
    """
    return ACTUAL_PORT


async def _run_ws_server(listen_host, listen_port):
    """
    Internal asyncio coroutine running websockets.serve.
    Input: listen_host (str), listen_port (int).
    Output: None.
    """
    global WS_LOOP, WS_SERVER, ACTUAL_PORT
    WS_LOOP = asyncio.get_running_loop()
    async with websockets.serve(_ws_handler, listen_host, listen_port) as server:
        WS_SERVER = server
        if server.sockets:
            ACTUAL_PORT = server.sockets[0].getsockname()[1]
        SERVER_READY.set()
        print(f"  [OK] WebSocket telemetry broadcaster active on ws://{listen_host}:{ACTUAL_PORT or listen_port}")
        await asyncio.Future()


def start_websocket_server(host=WS_HOST, port=WS_PORT):
    """
    Spawns the WebSocket server on a dedicated daemon background thread.
    Input: host (str), port (int).
    Output: Thread object or None if websockets package is not installed.
    """
    if not HAS_WEBSOCKETS:
        print("  [!] Warning: 'websockets' library is not installed. WebSocket broadcasting disabled.")
        return None

    SERVER_READY.clear()

    def worker_loop():
        try:
            asyncio.run(_run_ws_server(host, port))
        except Exception as exc:
            print(f"  [!] WebSocket server error: {exc}")

    server_thread = threading.Thread(target=worker_loop, daemon=True, name="TelemetryWebSocketBroadcaster")
    server_thread.start()
    SERVER_READY.wait(timeout=3.0)
    return server_thread
