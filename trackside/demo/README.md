# Trackside Virtual Lap Simulator & Live Telemetry Visualizer

This demo utility simulates realistic karting laps, corner by corner, generating authentic lateral-g telemetry and driving **three destinations simultaneously from a single source of truth**:

1. **Local WebSocket Broadcaster (`ws://127.0.0.1:8765`)**: Streams live JSON readings `{lap, zone, g_force, stage, speed_kmh, track_progress}` directly into the companion `track_visualization.html` browser dashboard.
2. **Bridge ESP32 over USB Serial**: Relays each reading over ESP-NOW to the physical Glove Unit (triggering real green/amber/red LEDs and buzzer haptics). **Fault-tolerant:** if no hardware is attached, the script logs a notice and continues streaming smoothly.
3. **Django Backend (REST API)**: POSTs authenticated telemetry to `/api/sessions/<id>/telemetry/` so live sessions, zone statistics, and alert logs appear in the Coach and Driver dashboards.

---

## 1. Requirements

Install required dependencies:
```bash
pip install websockets pyserial requests python-dotenv
```

*(Note: When using the local virtual environment, use `..\backend\venv\Scripts\pip install websockets pyserial requests python-dotenv`).*

---

## 2. Quick Start: Visual Demo (No Hardware Required)

You can launch the live browser visualizer in under 10 seconds:

### Step 1: Open the Visualizer in your Browser
Simply double-click or open `track_visualization.html` in Chrome/Edge/Firefox:
```bash
# Windows
start track_visualization.html

# macOS
open track_visualization.html

# Linux
xdg-open track_visualization.html
```
The page connects automatically to `ws://127.0.0.1:8765` and will wait for telemetry.

### Step 2: Start the Lap Simulator
Run the simulator from this `demo` directory:
```bash
python virtual_lap_simulator.py --continuous
```
* **Bridge ESP32 Connected:** Data streams to hardware LEDs + WebSocket visualizer + Backend.
* **No ESP32 Attached:** Automatically skips Serial without crashing, streaming live to `track_visualization.html`.

---

## 3. Companion Visualizer Features (`track_visualization.html`)

* **Single Self-Contained File:** Zero npm/build dependencies; runs directly as static HTML/CSS/JS.
* **Trackside Visual Language:** Pit-wall dark palette (`#0A0E13`, panels `#12181F`/`#161D26`, accent cyan `#3FA6E0`).
* **Dynamic SVG Circuit:** Moving kart dot synchronized by `track_progress` (0.0–1.0) using SVG `getPointAtLength()`, with active corner highlights (Hairpin, Sweeper, Chicane, Straights).
* **5-Segment Signal Strip:** Exact mirror of the physical glove's progressive lighting:
  * **Nominal:** 2 segments lit (Green, Green)
  * **Monitoring:** 4 segments lit (Green, Green, Amber, Amber)
  * **Intervene:** 5 segments lit (Green, Green, Amber, Amber, Red with pulse alert)
* **Live Telemetry Readouts:** Digital dials for Lateral G, Velocity (km/h), Current Lap, and Active Sector.
* **Rolling Waveform:** Real-time canvas sparkline tracking the last 60 lateral-g readings against the zone limit.
* **Scrolling Alert Log:** Automatic event recorder logging every `INTERVENE` threshold breach.
* **Auto-Reconnect:** Transparent reconnection loop every 2s if the simulator restarts.

---

## 4. Full-Stack Setup (Hardware & Backend Integration)

To connect the simulator to real hardware and persist telemetry into the Trackside database:

### 1. Configure Environment Variables
Create or edit `.env` in this directory (or use root `.env`):
```env
SERIAL_PORT=COM5
SERIAL_BAUD=115200
BACKEND_URL=http://localhost:8000
DEVICE_TOKEN=your_device_token_here
SESSION_ID=your_session_uuid_here
WS_HOST=127.0.0.1
WS_PORT=8765
```

### 2. Auto-Create Session via Token
Instead of manually copying a Session UUID, the script can create one on the fly using an Admin or Coach token:
```bash
python virtual_lap_simulator.py --create-session --admin-token <JWT_TOKEN>
```

### 3. Dry-Run (Skip Serial Port Explicitly)
```bash
python virtual_lap_simulator.py --dry-run
```

---

## 5. Command-Line Options

| Flag | Default | Description |
|---|---|---|
| `--continuous` | `False` | Run laps continuously until stopped with `Ctrl+C` |
| `--laps <N>` | `5` | Set total number of laps (set `0` for continuous) |
| `--delay <seconds>` | `0.2` | Interval between telemetry readings (e.g. `0.1` for faster pace) |
| `--ws-host <host>` | `127.0.0.1` | Local WebSocket host address |
| `--ws-port <port>` | `8765` | Local WebSocket broadcaster port |
| `--dry-run` | `False` | Skip opening Serial port explicitly |
| `--create-session` | `False` | Auto-create a performance session in backend |
| `--admin-token <token>` | `None` | JWT auth token for session auto-creation |

---

## 6. WebSocket Protocol Format

Each reading broadcast by `virtual_lap_simulator.py` uses this standardized JSON schema:

```json
{
  "lap": 1,
  "zone": "Hairpin",
  "g_force": 1.28,
  "stage": "INTERVENE",
  "speed_kmh": 51.4,
  "track_progress": 0.1667,
  "threshold": 1.15
}
```
