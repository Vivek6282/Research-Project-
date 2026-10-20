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

### One-Click Demo Launcher (Windows)
Double-click `run_demo.bat` in this `trackside/demo` directory to automatically launch the live browser visualizer and start the virtual lap simulator in continuous mode.

Alternatively, launch manually:

### Step 1: Open the Visualizer in your Browser
The live visualizer now lives at `frontend/public/demo/track_visualization.html` and opens at `/demo/track_visualization.html` when the frontend is running.

Opening the file directly still works:
```bash
# Windows
start ../frontend/public/demo/track_visualization.html

# macOS
open ../frontend/public/demo/track_visualization.html

# Linux
xdg-open ../frontend/public/demo/track_visualization.html
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

## 4. Storing a demo run

The physical glove and companion browser visualizer work seamlessly with or without the backend connected. When the backend is configured, the simulator asynchronously batches and records telemetry into the database without slowing down the simulation or the physical glove, allowing live session results, zone breakdowns, and alert logs to appear in the Coach and Driver dashboards.

To store a demo run:
1. **Seed Demo Circuit & Session:**
   In `trackside/backend`, run:
   ```bash
   python manage.py seed_demo --driver-email <driver>
   ```
2. **Configure Environment:**
   Paste the printed lines directly into `trackside/demo/.env` (see `.env.example` for placeholders and reference).
3. **Start the Backend:**
   In `trackside/backend`:
   ```bash
   python manage.py runserver
   ```
4. **Run the Simulator:**
   In `trackside/demo`:
   ```bash
   python virtual_lap_simulator.py --continuous
   ```
   *(Or double-click `run_demo.bat` on Windows)*.
5. **Open Dashboards:**
   Open the Driver and Coach dashboards in your browser to inspect live lap times, speed graphs, zone thresholds, and alert events.

---

## 5. Command-Line Options

| Flag | Default | Description |
|---|---|---|
| `--continuous` | `False` | Run laps continuously until stopped with `Ctrl+C` |
| `--laps <N>` | `5` | Set total number of laps (set `0` for continuous) |
| `--delay <seconds>` | `0.2` | Interval between telemetry readings (e.g. `0.1` for faster pace) |
| `--limit <NAME=VALUE>` | `[]` | Custom corner limit, repeatable (e.g. `--limit Hairpin=1.00`) |
| `--ws-host <host>` | `127.0.0.1` | Local WebSocket host address |
| `--ws-port <port>` | `8765` | Local WebSocket broadcaster port |
| `--dry-run` | `False` | Skip opening Serial port explicitly |
| `--create-session` | `False` | Auto-create a performance session in backend |
| `--admin-token <token>` | `None` | JWT auth token for session auto-creation |

---

## 6. Custom corner limits

Coaches can configure stricter cornering g-force limits (e.g. a cautious profile for beginners or wet track conditions) so the glove, visualizer, and backend dashboards all evaluate against the same safety limits.

### Allowed Range and Safety Rules
* **Range per corner:** `1.00 g` up to that corner's default, inclusive, with at most 2 decimal places:
  * **Hairpin:** `1.00` to `1.15 g` (default: `1.15 g`, cautious preset: `1.00 g`)
  * **Sweeper:** `1.00` to `1.55 g` (default: `1.55 g`, cautious preset: `1.32 g`)
  * **Chicane:** `1.00` to `1.30 g` (default: `1.30 g`, cautious preset: `1.10 g`)
* **Why:** Trackside enforces a strict safety rule: a coach may tighten a threshold to increase safety, but a custom threshold can never exceed the zone's calibrated physical safety limit (never above default). Limits cannot be set below `1.00 g` (the plausible sprint-kart cornering floor).

### The `--limit` Flag
The simulator accepts repeatable `--limit NAME=VALUE` flags from the CLI:
* `NAME`: `Hairpin`, `Sweeper`, or `Chicane` (case-insensitive).
* `VALUE`: float between `0.50` and `2.50`.
* Unknown corner names or malformed values exit immediately with code `2`.

**Example:**
```bash
python virtual_lap_simulator.py --continuous --limit Hairpin=1.00 --limit Sweeper=1.32 --limit Chicane=1.10
```

### Precedence Order
At start-up, the simulator resolves corner limits using the following precedence (highest to lowest):
1. **`--limit` CLI flag** (custom limit specified for this run)
2. **Backend zone threshold** (fetched from backend at start-up if `SESSION_ID` is configured)
3. **Built-in default** (`1.15 g` Hairpin, `1.55 g` Sweeper, `1.30 g` Chicane)

Start-up logs clearly declare the limit in force and its origin for each corner:
```
Hairpin limit 1.00 g (custom)
Sweeper limit 1.55 g (backend zone)
Chicane limit 1.30 g (default)
```

### Backend Synchronization (`SESSION_ID`)
When started from the Demo Control panel on `/demo/track_visualization.html`, custom limits are automatically synchronized with the backend:
* The backend reads `SESSION_ID` from `trackside/demo/.env` via `dotenv_values` (without polluting the process environment).
* If `SESSION_ID` resolves to a valid session, the backend checks the driver's current active threshold for each zone. If the requested limit differs from the active threshold, a new row is inserted into `DriverZoneThreshold` (`driver=session.driver, zone=zone, custom_threshold_g=limit, set_by=coach`) wrapped in `transaction.atomic()` with `full_clean()` validation.
* Because the table is insert-only, existing rows are never modified, and no insert occurs if limits have not changed.
* If `SESSION_ID` is missing or the session cannot be found, sync is skipped and reported in the status note.

### Alert Discrepancy Warning (Manual CLI Execution)
Backend alert ingestion always evaluates telemetry against the zone's calibrated limit or the driver's active `DriverZoneThreshold` stored in the database.

If you launch the simulator from a terminal with a value **above** a zone default (for example `--limit Hairpin=1.40`), the simulator and physical glove will use `1.40 g`, but backend alerts will trigger at the calibrated `1.15 g`. This causes the backend alerts on the dashboard to differ from the glove's LED signals. To keep the glove, visualizer, and backend dashboards in complete synchronization, always configure limits through the Demo Control panel or keep values within allowed ranges.

---

## 7. WebSocket Protocol Format

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

---

## 8. Run Lifecycle, Session Closing & Known Limits

### Event Lifecycle Protocol
Before telemetry begins and upon run conclusion, the simulator broadcasts non-reading lifecycle events over WebSocket:
* **`run_start`**: `{"type": "run_start", "mode": "laps" | "continuous", "total_laps": N or null}`
  * Prompts the visualizer to clear past alerts, reset the lap counter, and display the target lap count (or no denominator in continuous mode).
* **`run_end`**: `{"type": "run_end"}`
  * Notifies the visualizer that the run is complete, pinning track progress to 100% and updating session status to finished.

### Session Closing & Hard Terminate Limit
When a run completes (or is halted cleanly with Ctrl+C in continuous mode), the simulator flushes remaining telemetry batches and automatically closes the backend session via `POST /api/sessions/<id>/finish/` using the device token, setting `ended_at = now`. This finalizes best-lap calculations (including the final lap) and marks the session as completed in the Coach and Driver dashboards.

**Known Limit (Windows Hard Terminate)**:
If the simulator process is forcefully killed (such as closing the console window abruptly or terminating the process via Windows Task Manager without allowing Ctrl+C cleanup to run), process termination handlers cannot execute. A hard-stopped run leaves its session "In progress" in the database.

---

## 9. WebSocket Origin Security & Null Origin

The simulator validates incoming WebSocket connections using exact equality matching against configured origins (`http://localhost:5173` and `http://127.0.0.1:5173`). Prefix tricks (e.g. `http://127.0.0.1:51730` or `http://localhost:5173.evil.com`) are strictly rejected with close code 1008.

### The `null` Origin and `WS_ALLOW_NULL_ORIGIN` Setting
By default, the simulator allows connections with `Origin: null` (`WS_ALLOW_NULL_ORIGIN=true`) because `run_demo.bat` launches the visualizer file directly from the local filesystem (`file:///`), and browsers send `null` as the origin for local files.

However, a sandboxed web page in an attacker's browser can also send `null` as its origin. While the demo simulator runs on your laptop, such a page could potentially connect to `ws://127.0.0.1:8765` and read the simulated telemetry stream.

**To harden the setup**:
Set `WS_ALLOW_NULL_ORIGIN=false` in `demo/.env`. Then, do not open the visualizer directly from the disk; instead, open the visualizer from the Coach's Demo Tools button in the web frontend (served securely from `http://localhost:5173`).
