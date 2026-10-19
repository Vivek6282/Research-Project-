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


async def _run_ws_server(listen_host, listen_port):
    """
    Internal asyncio coroutine running websockets.serve.
    Input: listen_host (str), listen_port (int).
    Output: None.
    """
    global WS_LOOP
    WS_LOOP = asyncio.get_running_loop()
    async with websockets.serve(_ws_handler, listen_host, listen_port):
        print(f"  [OK] WebSocket telemetry broadcaster active on ws://{listen_host}:{listen_port}")
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

    def worker_loop():
        try:
            asyncio.run(_run_ws_server(host, port))
        except Exception as exc:
            print(f"  [!] WebSocket server error: {exc}")

    server_thread = threading.Thread(target=worker_loop, daemon=True, name="TelemetryWebSocketBroadcaster")
    server_thread.start()
    time.sleep(0.3)
    return server_thread
