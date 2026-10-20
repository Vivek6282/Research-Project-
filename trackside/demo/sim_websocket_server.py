"""
Trackside Virtual Lap Simulator — WebSocket Broadcaster.
Hosts a local WebSocket server to stream real-time lap telemetry directly to companion
visualizers such as frontend/public/demo/track_visualization.html.
"""

import asyncio
import json
import threading
import time

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

from sim_config import WS_HOST, WS_PORT, WS_ALLOWED_ORIGINS
from sim_track import TRACK

CONNECTED_CLIENTS = set()
WS_LOOP = None
LATEST_RUN_START = None
RUN_START_LOCK = threading.Lock()
WS_SERVER = None
SERVER_READY = threading.Event()
ACTUAL_PORT = None


async def _ws_handler(websocket):
    """
    Handles incoming WebSocket connections and enforces origin check.
    Input: websocket connection instance.
    Output: None.
    """
    origin_header = None
    if hasattr(websocket, "request_headers"):
        origin_header = websocket.request_headers.get("Origin")
    elif hasattr(websocket, "request") and hasattr(websocket.request, "headers"):
        origin_header = websocket.request.headers.get("Origin")

    if origin_header is not None and "*" not in WS_ALLOWED_ORIGINS:
        is_origin_allowed = origin_header in WS_ALLOWED_ORIGINS or any(origin_header.startswith(allowed_origin) for allowed_origin in WS_ALLOWED_ORIGINS)
        if not is_origin_allowed:
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
