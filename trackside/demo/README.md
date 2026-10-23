# Trackside Virtual Lap Simulator & Live Telemetry Visualizer

This demo utility simulates realistic karting laps, corner by corner, generating authentic lateral-g telemetry and driving **three destinations simultaneously from a single source of truth**:

1. **Local WebSocket Broadcaster (`ws://127.0.0.1:8765`)**: Streams live JSON readings `{lap, zone, g_force, stage, speed_kmh, track_progress}` directly into the companion `track_visualization.html` browser dashboard.
2. **Bridge ESP32 over USB Serial**: Relays each reading over ESP-NOW to the physical Glove Unit (triggering real green/amber/red LEDs and buzzer haptics). **Fault-tolerant:** if no hardware is attached, the script logs a notice and continues streaming smoothly.
3. **Django Backend (REST API)**: POSTs authenticated telemetry to `/api/sessions/<id>/telemetry/` so live sessions, zone statistics, and alert logs appear in the Coach and Driver dashboards.

---

## 0. Recommended: play a demo from the Coach "Maps & Demo" tab

Everything about maps and demonstrations lives in the Coach screen, not in Settings.

**One-time setup (development machine only, never production):**
1. In `trackside/backend/.env` set `DEMO_TOOLS_ENABLED=true` and keep `DJANGO_ENV=development`. Restart the backend.
2. In `trackside/frontend/.env` set `VITE_ENABLE_DEMO_TOOLS=true` (see `.env.example`). Restart `npm run dev`.
3. Leave `SERIAL_PORT=auto` in `trackside/demo/.env` (copy `.env.example`): the simulator finds the bridge board whatever COM number Windows gave it (see "COM ports keep changing" below). Close the Arduino Serial Monitor first: only one program can use a COM port.
4. Install the demo requirements: `pip install -r trackside/demo/requirements.txt` (use the Python that runs the backend, or set `DEMO_PYTHON`).

**Each demo:**
1. Sign in as a **Coach**, open **MAPS & DEMO**.
2. The **Demo Circuit** (the simulator's built-in map, badges *Built-in* and *Simulator map*) is the first card; every custom map follows. **Add track** imports a new one from a RaceChrono CSV or VBO file.
3. Press **Play demo** on a card, choose an **active driver**, the **laps** (1 to 20) and the **pace**:
   * **safe**: every corner stays green, **edge**: amber at every corner, **over**: red alerts at every corner.
   * Pace applies to custom maps only; the Demo Circuit keeps its own fixed demo pattern.
4. The panel shows *Running, lap x of y*, whether the glove bridge is connected, and the buttons **Stop**, **Watch live** (jumps to the Live Pit-Wall Console with that driver selected) and **Open live visualizer**.
5. The glove reacts exactly as before: the simulator still sends `g,STAGE` lines to the bridge on `SERIAL_PORT`, now using the chosen map's corners.

**What the server does for you when you press Start** (so there is nothing to copy by hand any more):
* creates a new session for the driver on that map, marked **Demo run** (shown in the Coach and Driver history so it is never mistaken for real driving);
* uses one dedicated device, **"Demo kart unit"**, assigned to the chosen driver only for the run (refused, with the unit named, if that driver already holds a different kart unit). When the demo ends or is stopped the device is unassigned and its token is thrown away;
* gives the run a fresh API token. The token, session id, backend URL and corner list reach the simulator **only as environment variables** (never on the command line), and they win over anything in `demo/.env`;
* writes the custom map's profile file to `trackside/backend/demo_profiles/<map id>.json` and starts the simulator with a fixed command, no shell;
* allows **one demo at a time** (a second Start is refused) and closes the session when the run ends.

If either switch is off, or the server is in production, the tab still shows the maps and the corner editor but hides every Play, Stop and visualizer control.

### Marking the highest-g corners (Edit corners)
On a custom map press **Edit corners**: the outline opens large with green **+** suggestions at the tightest point of each bend (where g is highest at a given speed). Click a **+** to accept it or click anywhere on the outline to add a corner, drag a number along the line, rename it (required, up to 40 characters), set its limit (0.3 to 1.5 g) and its zone length (10 to 100 m, default 30 m centred on the point). The list shows each corner's radius and the safe corner speed at the current limit: `sqrt(limit x 9.81 x radius)`. Every saved corner becomes an alert zone that the alert rule and the glove use. A corner that already has telemetry or alerts is hidden instead of deleted, and limit changes are kept in an insert-only history. The Demo Circuit is view-only; use **Duplicate as custom map** to get an editable copy.

### Watching a demo in the Coach module

1. Coach, **Maps & Demo** tab, **Play demo** on a map, choose the driver and laps, **Start demo**.
2. The page switches to the live tab by itself with that run's driver selected (the **Watch live** button on the Maps tab does the same later). Nothing else switches drivers automatically.
3. In the **Live Track View** card you see:
   * **Readout row** under the header: **LAP**, **CORNER** (name and type, or "Straight"), **G** with the limit in force ("limit 1.15 g", or "No limit" on a straight) and **SPEED**.
   * The **map** with the moving dot and the highlighted corner (unchanged).
   * **LATERAL-G WAVEFORM (3 s)**: the last 3 seconds of lateral g, coloured by the current stage, with a dashed red line at the limit and a dashed amber line at 82% of it.
   * **ALERTS** log: the amber and red alerts that arrive live, newest first. **Clear** only empties this list on your screen; nothing is deleted on the server.
4. The limit shown is the **corner's limit set on the map** (Maps, Edit corners) for the corner the kart is in, worked out by the server with the same rule as the alerts and the glove. A straight has no limit and stays nominal.
5. Before any data arrives the panels say "Waiting for live data", "No alerts yet" or "-"; no numbers are invented.


### Glove demo with a hosted site: Play demo + Connect bridge (no scripts)

On the hosted site (Render) the server runs the virtual race itself and your **browser** talks to the bridge over USB (Web Serial), so there is nothing to copy and no script to run.

1. Use **Chrome or Edge** on the laptop (Firefox and Safari do not support Web Serial). Open the hosted site, wait for it to wake, and log in as Coach.
2. Plug in the bridge (and switch the glove on).
3. Press **Connect bridge** in the bar at the top (next to LIVE WS STREAM). The browser lists the USB ports: choose a **CP210x** one. The site checks the board's banner: if you chose the glove it says so, press Connect bridge again and pick the other one. The chip turns green: **GLOVE BRIDGE CONNECTED**. Next time the page reconnects a port you chose before by itself.
4. **Maps & Demo > Play demo** on the Demo Circuit, choose the driver and Start. You land on the live tab; the server runs the simulator and the browser sends each reading's stage to the bridge, so the glove follows the run.
5. Stop it with **Stop** on the Maps & Demo tab.

Needs the server setting `HOSTED_DEMO_ENABLED=true` (the Render blueprint sets it; remove it or set it to false to switch the hosted demo off). Only a Coach can start a run. The glove lags the screen by a fraction of a second. If the bridge is busy, close the Arduino Serial Monitor. The "Connect laptop" method below is only a fallback: its box appears on the Maps & Demo tab only when the Play demo is not available on that server.

### Glove demo with a hosted site ("Connect laptop")

The glove only talks to the bridge on a laptop, so with a hosted site the laptop's simulator does both jobs: it drives the glove and posts the same readings to the hosted server. The hosted Coach screen then shows the run live.

1. **Wake the site** (a free Render service sleeps when idle): open it a minute early and log in as Coach.
2. **Coach > Maps & Demo > Connect laptop:** choose the driver and press **Start link**. The panel shows four lines (`BACKEND_URL`, `SESSION_ID`, `DEVICE_TOKEN`, `DEMO_ZONES`); the token is hidden until you press **Show token** and is shown only now.
3. **On the laptop, the easy way:** press **Copy lines** on the site, then double-click `trackside\demo\run_hosted_demo.bat` (or run `py hosted_demo.py` in `trackside\demo`). It reads the copied lines from the clipboard, writes them into `.env` (nothing else in the file changes), never prints the token, and then starts the simulator with `--post-batch 4` (steps 4 and 5 below are then done for you, except plugging in the bridge). **If the clipboard does not work:** press **Show token** on the site, then run `py hosted_demo.py --paste`, paste the four lines into the window, press Enter, then Ctrl+Z and Enter. **By hand instead:** open `trackside\demo\.env` and replace those four lines with the ones from the panel. Keep `SERIAL_PORT=auto`.
4. **Plug in the bridge**, switch the glove on, close the Arduino Serial Monitor, and check `py virtual_lap_simulator.py --list-ports` shows `bridge`.
5. **Run** in `trackside\demo`: `py virtual_lap_simulator.py --post-batch 4 --laps 5`. The glove's LED follows the stages.
6. **On the site:** the panel says "Receiving readings from the laptop"; press **Watch live** to see the dot, readouts, waveform and alerts. The run is marked DEMO RUN.
7. When the simulator finishes it closes the session. **End link** also closes it and cancels the token. A new **Start link** always replaces the old one.

Why `--post-batch 4` and not 1: over the internet a request takes longer than the 0.2 s between readings, so one request per reading falls behind and readings are lost when the run ends (a real rehearsal: sent 101, unsent 139). Four per request keeps up. If the summary still shows `unsent` above 0, use `--post-batch 6`.

Notes: only a Coach or Admin can start a link; the token only works as that device (posting readings and finishing sessions for that driver) and stops working when the link ends. The server never runs the simulator. Do a full rehearsal the day before.

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

## 4. Storing a demo run (manual, from a terminal)

The Coach "Maps & Demo" tab does all of this for you (section 0). This manual route is for running the simulator by hand from a terminal.

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
| `--limit <NAME=VALUE>` | `[]` | Custom corner limit for the built-in track, repeatable (e.g. `--limit Hairpin=1.00`) |
| `--track-file <path>` | none | Run a custom map from a profile file made by `python manage.py export_track <track_id> --out <path>`. Without it the built-in Demo Circuit runs exactly as before |
| `--pace safe\|edge\|over\|mixed` | `safe` | With `--track-file`: 0.85 / 0.95 / 1.08 of each corner's safe speed (green / amber / red); `mixed` gives each lap a few amber and red corners among green ones |
| `--seed <N>` | random | With `--track-file`: makes a run repeatable (laps still differ from each other by about 3% of g) |
| `--cruise-kmh <N>` | `80` | With `--track-file`: straight-line speed (20 to 200) |
| `--post-batch <N>` | `10` | Most readings sent in one backend POST (1 to 10). `1` posts every reading on its own as soon as it is ready. A bad value exits with code 2. Terminal runs keep the default |
| `--list-ports` | off | Print every serial port with its description, VID:PID, serial number and what it is (bridge, glove, ...), then exit. Nothing else runs (no simulation, no network, no backend) |
| `--ws-host <host>` | `127.0.0.1` | Local WebSocket host address |
| `--ws-port <port>` | `8765` | Local WebSocket broadcaster port |
| `--dry-run` | `False` | Skip opening Serial port explicitly (no port is searched or opened) |
| `--create-session` | `False` | Auto-create a performance session in backend |
| `--admin-token <token>` | `None` | JWT auth token for session auto-creation |


> **Why the Play demo uses `--post-batch 1`:** with the default the backend worker sends up to 10 readings at once (or after 1 second), so the Coach live screen receives them in bursts about once a second and the dot jumps. The Coach "Play demo" button always passes `--post-batch 1` so each reading reaches the Coach screen as it happens (about 5 per second). Runs started from a terminal without the flag behave as before.


### COM ports keep changing

Windows gives the boards different COM numbers when cables move, so a fixed `SERIAL_PORT=COM5` often points at the wrong board. The glove ignores USB, so when the port is the glove it just stays on its dim blue LED.

**`SERIAL_PORT=auto`** (the default; also an empty value) makes the simulator look for the bridge itself. It opens each candidate port, resets the board the standard ESP32 way and reads its startup banner (`TRACKSIDE BRIDGE` or `TRACKSIDE GLOVE`). It never writes anything to a port and stops at the first bridge (at most 20 seconds in total, 4.5 seconds per port). If you name a port (for example `SERIAL_PORT=COM5`) that port is checked first; if it is the glove, busy or silent, the other ports are searched and the run prints `[i] COM5 is the glove; the bridge was found on COM7. Using COM7.` If no bridge is found the run continues without the glove and lists what each port answered.

**See what is plugged in:** `py virtual_lap_simulator.py --list-ports` prints a table of every serial port (name, description, VID:PID, serial number, verdict) and exits.

| Verdict | Meaning |
|---|---|
| `bridge` | This is the Bridge ESP32. It will be used. |
| `glove` | This is a glove board, not the bridge. |
| `unknown` | The port opened but no Trackside banner came (wrong board, old firmware, or a port that is not a board). |
| `busy` | Another program has the port, or access was refused. **Close the Arduino Serial Monitor** (and any other serial tool) and try again. |
| `error` | The port could not be opened or did not answer in time (the detail says why). |

**The cache file:** the last good port is remembered in `trackside/demo/.last_bridge_port` (git-ignored) and tried early next time. It is only a hint: the banner is always checked again. Delete the file any time. `TRACKSIDE_PORT_CANDIDATES=COM3,COM7` (comma-separated) replaces the port discovery for unusual systems.

**Other devices on this laptop:** to find the bridge the search opens each serial port and resets the board on it (the standard ESP32 reset). That is harmless for the Trackside boards but restarts any other device on a port it tries, for example a 3D printer controller. `TRACKSIDE_PORT_SKIP=COM3,COM4` (comma-separated) makes the search never open those ports. Choosing a port yourself (`SERIAL_PORT=COMx`) still opens exactly that one.

**Pin a COM number in Windows (optional):** Device Manager, Ports (COM & LPT), right-click the board, Properties, Port Settings, Advanced, then choose a COM port number that is free. Put the same number in `SERIAL_PORT` if you want to force it.

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

### Limits on custom maps
A custom map uses **each corner's own limit**, set in the corner editor (Coach > Maps & Demo > Edit corners, 0.3 to 1.5 g). `--limit` is only for the built-in Demo Circuit and cannot be combined with `--track-file`.

### Alert Discrepancy Warning (Manual CLI Execution)
Backend alert ingestion always evaluates telemetry against the zone's own limit (`zone.threshold_g`, set on the map). Old per-driver limits are no longer used.

If you launch the simulator from a terminal with a value **above** a zone default (for example `--limit Hairpin=1.40`), the simulator and physical glove will use `1.40 g`, but backend alerts will trigger at the calibrated `1.15 g`. This causes the backend alerts on the dashboard to differ from the glove's LED signals. To keep the glove, visualizer, and backend dashboards in complete synchronization, keep `--limit` values within the allowed ranges.


### Where limits come from

* A corner's g-force limit is set **on the map**: Maps, then **Edit corners** (0.3 to 1.5 g). It is stored as the corner's own limit and applies to **everyone** who drives that map.
* The alerts, the live Coach screen, the simulator (and so the glove and the visualizer) and the Play demo status ("Map limits: Hairpin 1.05 / Sweeper 1.30 / Chicane 1.10") all use that same limit.
* The built-in **Demo Circuit is locked**: to change its limits, **Duplicate as custom map** and edit the copy. The built-in run uses the simulator's own track and fixed defaults, so the Play demo passes no `--limit` for it.
* **Per-driver limits are retired.** Old per-driver rows stay in the database as history and are ignored; creating a new one (`POST /api/drivers/thresholds/`) answers `410 Gone`.

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

### Live events (backend to the Coach screen)

The backend sends these over `/ws/sessions/<session id>/telemetry/`. Every message is
`{"type": ..., "data": {...}}` and all values are plain JSON (ids and times are strings).
This is separate from the simulator's own visualizer socket above.

`telemetry_reading` - one per stored reading, in `recorded_at` order:

```json
{
  "type": "telemetry_reading",
  "data": {
    "id": "...", "session": "...", "zone": "<zone id or null>",
    "recorded_at": "2026-10-22T10:00:00.200000Z",
    "lateral_g": 1.28, "speed_kmh": 51.4, "gps_lat": 10.0007, "gps_lng": 76.0003, "lap_number": 1,
    "threshold": 1.15, "stage": "intervene", "zone_label": "Hairpin", "corner_type": "hairpin"
  }
}
```

The last four keys exist only in this live message (they are not stored and not in the REST output):

* `threshold` - the limit in force: the corner's own limit set on the map. `null` on a straight.
* `stage` - `nominal`, `monitoring` (amber) or `intervene` (red), from the same rule as the alerts (`alerting.stage_for`). A straight is `nominal`.
* `zone_label`, `corner_type` - the corner's name and type, `null` on a straight.

`alert_triggered` - one per new amber or red alert:

```json
{"type": "alert_triggered", "data": {"id": "...", "session": "...", "zone": "...", "zone_label": "Hairpin",
 "severity": "red", "g_value": 1.28, "threshold_applied": 1.15, "triggered_at": "2026-10-22T10:00:00.200000Z"}}
```

`biometric_reading` - one per stored biometric reading:

```json
{"type": "biometric_reading", "data": {"id": "...", "session": "...", "recorded_at": "...",
 "heart_rate": 92, "spo2": 98, "breathing_rate": 16}}
```

---

## 8. Run Lifecycle, Session Closing & Known Limits

### Event Lifecycle Protocol
Before telemetry begins and upon run conclusion, the simulator broadcasts non-reading lifecycle events over WebSocket:
* **`run_start`**: `{"type": "run_start", "mode": "laps" | "continuous", "total_laps": N or null}`
  * Prompts the visualizer to clear past alerts, reset the lap counter, and display the target lap count (or no denominator in continuous mode).
  * A `--track-file` run adds `"track_name"`, `"outline"` (at most 2,000 `[x, y]` points in metres) and `"corners"` (`{label, start_index, end_index, label_index}`), and the visualizer draws that map with its corner labels. Late joiners get the same message replayed. Without an outline the visualizer draws the default track.
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
Set `WS_ALLOW_NULL_ORIGIN=false` in `demo/.env`. Then, do not open the visualizer directly from the disk; instead, open the visualizer from Coach > Maps & Demo > **Open live visualizer** in the web frontend (served securely from `http://localhost:5173`).

---

## 10. Automated Tests

### Visualizer Alert Deduplication Tests (Node.js)
The visualizer alert deduplication logic is tested using Node.js:
* **Command**: `node --test tests/demo/test_alerts.test.mjs` (run from `trackside/frontend/`)
* **Minimum Node.js Version**: `Node.js >= 18.0.0` (uses built-in `node:test` and `node:assert`)

### Visualizer Map Geometry Tests (Node.js)
* **Command**: `node --test tests/demo/test_map_geometry.test.mjs` (run from `trackside/frontend/`)

### Simulator Tests (Python)
The WebSocket replay and origin suites, the track profile loader, the physics (pace, seed, smoothness, `g,STAGE` line format) and the `.env` priority rule are tested using Python `unittest`/`pytest`:
* **Command**: `python -m pytest tests` (run from `trackside/demo/`)
* **Requirements**: Python environment with `websockets`, `requests`, `python-dotenv` and `pytest` installed
