# Trackside — Phase 2 Master Prompt (supersedes `PHASE2_BUILD_BRIEF.md`)

How to use this file: send **Part 0** with **one** phase at a time (2.0, then 2.1, …) to the coding agent. Wait for its report, check it, then send the next phase. Parts A to C at the end are reference for you, not for the agent.

Tags used below: **[Verified]** established fact; **[Estimate]** calculated or rough figure; **[Assumption]** chosen default, with what goes wrong if it is false; **[Verify vs. Datasheet]** must be checked against the part's datasheet before wiring or coding.

---

## Part 0 — Context and rules (send with EVERY phase)

You are extending **Trackside**, an existing system in `trackside/`: Django 5.2 + DRF + Channels (Daphne) backend, React 19 + Vite + Tailwind PWA frontend, a Python lap simulator in `demo/`, and ESP32 firmware in `firmware/` (bridge + glove over encrypted ESP-NOW). Phase 1 is complete and verified. Before changing anything, read `trackside/README.md`, `backend/README.md`, `frontend/README.md`, `demo/README.md`, `firmware/README.md` and `Trackside_Handoff_Package/trackside_handoff/PHASE2_BUILD_BRIEF.md`. Extend what exists; never rewrite working Phase 1 code.

**Already in the code, reuse it (do not create duplicates):**
- Models: `BiometricReading` (heart_rate, spo2, breathing_rate, recorded_at), `DeviceCommand` (command_type, status, requested_by, requested_at, completed_at, result), `SessionNote` (coach, zone, note_text; UI parked), `Session.goal_text` / `goal_passed` / `mode` / `is_demo`, `Device` (device_type glove / kart_unit / biometric_strap, assigned_to, last_seen_at, api_key_hash), `ZoneThresholdHistory` (insert-only).
- Telemetry ingestion with device tokens, batch limit 100, range checks, one alert per corner crossing, corner deltas, best lap, WebSocket push (`telemetry_reading`, `alert_triggered`), deny-by-default access helpers in `driving_sessions/access.py`.
- Browser serial "Connect bridge" (`frontend/src/lib/bridge-serial.ts`), laptop link endpoints, drawn and imported GPS maps (Leaflet), demo control, hosted demo switch.

**Rules (non-negotiable, carried over from Phase 1):**
1. Work only on the branch named in the phase and push only to that branch. Never push to `main`, never merge, never force-push.
2. No file over 300 lines; every function and component has a short plain-English comment; descriptive names.
3. Default-deny API: every new endpoint has explicit permission classes, an ownership check (no IDOR; a missing and a forbidden object return the identical 404), input validation with stated ranges, rate limiting where data is posted, and an entry in `accounts/tests/test_access_sweep.py`.
4. Django ORM only; no raw SQL; no `dangerouslySetInnerHTML`; no secrets, keys or passwords in code, commits, logs or command lines.
5. Every feature ships with tests. Before each commit, the full backend suite, `vitest`, the demo tests and `VITE_ENABLE_DEMO_TOOLS=true npm run build` pass. Test counts may only go up.
6. The serial input line `g,STAGE` and the stage rule (INTERVENE at or above the corner limit, MONITORING at or above 0.82 × limit, else NOMINAL) do not change. Any change to the rule needs the owner's written approval.
7. LED flash rates stay at or below 3 per second (photosensitivity). Vibration pulses follow the same timing.
8. Biometric values never appear on any shared or cross-driver view. Leaderboards and badges never show raw biometrics or raw speed.
9. **Firmware** (`trackside/firmware/`) is changed only in phases marked FIRMWARE, and only after the owner approves the design note for that phase.
10. Trackside is a coaching aid, not a safety system. No feature calls emergency services, and no screen implies that it does. Every crash or biometric screen states this.

**Report back (plain, no "should work"):** each task done / not done with what you verified; test counts before and after for every suite; line-count check; commit hashes; anything you could not verify, stated as such.

---

## Phase 2.0 — Groundwork and Phase 1 loose ends (software only)
Branch: `phase2-0-groundwork`. No new hardware.

0. **Repo survey first.** Write `docs/phase2/SURVEY.md`: for each Phase 2 item in this file, list what already exists (models, endpoints, screens, banners), what is missing, and the files you will touch. Stop and report before task 1 if anything here contradicts the code.
1. **Phase 1 open items.**
   a. `TC-ADMIN-07` expects no Delete button, but permanent delete with typed confirmation now exists. Ask the owner which rule stands; update the test or the feature accordingly.
   b. The Selenium suite uses fixed 3 s UI waits and 5 s API timeouts that time out on slow machines. Move all waits to one setting (default 10 s UI, 15 s API, overridable by environment variable) and re-run the suite three times; report flaky tests by name.
   c. If the corner-time fix (time each crossing, not each lap number) is not on `main`, port it here with its tests.
2. **Device events contract.** Add a `DeviceEvent` model and `POST /api/devices/events/` for device-originated events: `event_id` (UUID made on the device, unique, used for de-duplication), `event_type` (`crash_suspected`, `lost_contact`, `heartbeat`, `self_test_result`, `driver_ok`), `session` (nullable), `occurred_at` (device time) and `received_at` (server time, authoritative for ordering), `payload` (JSON, schema-validated per type, max 8 KB). A repeated `event_id` returns 200 with the stored event (idempotent), never a duplicate. Authentication: device token (kart unit, glove via bridge) or a signed-in Driver for their own active session (phone page). Rate limit per sender.
3. **Data retention and consent.** Academy settings (Admin only): retention period for telemetry, events and biometrics (default 12 months) with a scheduled purge command; a per-driver "consent recorded" flag and "under 18" flag. Biometric and phone-sensor features refuse to start for a driver without consent recorded.
4. **Time.** All new device payloads carry device time and a monotonic sequence number; the server stores both and its own receive time. Document which time each screen shows.

Done when: survey written, loose ends closed or decided, events endpoint live with idempotency and access-sweep tests, retention purge tested on fixtures.

---

## Phase 2.1 — Phone as a temporary kart unit (no new hardware)
Branch: `phase2-1-phone-unit`. Follows Workstream A of the existing brief, with these additions.

1. **Ingest:** a signed-in Driver posts batched readings to their own **active** session only, through the existing telemetry pipeline (same validation, alerts, corner detection, WebSocket). Session mode set by the Coach to `simulator` or `phone`; phone readings to a `simulator` session are refused (409).
2. **Phone Sensor page** (Driver, after sign-in): Start/Stop that requests motion and location permission (iOS needs a tap and HTTPS), Wake Lock, and shows connection, GPS accuracy, readings per second and queue length.
3. **Calibration:** "hold still" (gravity direction) then "drive straight" (forward axis); store per session; refuse to start if the phone moves in its mount (gravity direction changes by more than a set angle).
4. **Lateral g:** primary `speed (m/s) × yaw rate (rad/s) ÷ 9.81` **[Verified physics for steady cornering]**; cross-check with the calibrated sideways accelerometer; flag the session when they disagree for more than a few seconds.
5. **Position:** snap to the track outline between GPS fixes by speed × time; correct on each fix; show GPS accuracy on the coach map.
6. **Offline buffer:** readings queue on the phone when the network drops (bounded, oldest dropped first, count shown) and flush in order when it returns.
7. **Recorded fixtures:** store several real phone recordings in the repo as test data; test g and position maths against them.

Done when: a slow real kart run shows the live dot and corner alerts on the coach screen, and Connect bridge drives the glove from phone data.

---

## Phase 2.2 — Crash detection and coach alert (phone first)
Branch: `phase2-2-crash-alert`. Follows Workstream A2 of the existing brief, corrected and completed as below.

**Detection runs on the sending device** (phone now, kart unit in 2.5), on high-rate motion data, so it still works when the network is slow. One shared, versioned settings file holds every limit, with comments and tests; the phone and the kart unit read the same values.

State machine (all three stages must pass, within the stated windows):
1. **IMPACT:** total acceleration magnitude above the impact limit for at least the minimum burst, **or** the accelerometer reports its maximum value (saturation). Phone and low-range IMU accelerometers saturate (MPU-6050 maximum ±16 g **[Verified]**), so saturation itself counts as impact evidence; do not set the limit at or above the sensor's maximum.
2. **SUDDEN STOP:** within about 2 s after the impact, speed falls from above the moving speed to below the stopped speed (GPS speed and the integrated motion estimate must agree).
3. **AFTERMATH:** low motion for a few seconds **or** orientation more than a set angle from the calibrated mounting (possible rollover).

Separately: readings stop while the kart was above walking speed → `lost_contact` (lower level, never labelled a crash).

Delivery and alert:
- Send `crash_suspected` through the 2.0 events endpoint at once, ahead of queued readings, retried with bounded exponential backoff and jitter until the server confirms; the `event_id` makes retries safe. Payload: device time, last position, speed before, peak g, saturation flag, and the raw window (a few seconds either side) for review.
- Coach screen: full-width red banner on every open coach screen with driver, time and a map pin; stays until a coach presses **Acknowledge** (who and when go to the audit log). Browsers block sound until the user interacts, so the console shows an **Enable alert sound** button once per visit and a visible warning while sound is off. Repeat the sound every 30 s until acknowledged.
- Driver phone page: large **I'm OK** button after a detected crash; marks the event "driver OK" for the coach but never clears the coach's alert.
- Records: crash events list per session (Coach/Admin all; Driver own only) with the raw window, acknowledgement and an optional note.
- No internet at the track: the alert reaches the coach only through a server they can reach. Document and support the fallback of running the stack on a trackside laptop with its own Wi-Fi.

Tests without crashing a kart: recorded fixtures for hard braking, kerb strikes, bumps, spins and a cushioned drop test of the mounted phone, plus a simulator `crash` scenario. Tests must prove that braking, kerbs and bumps raise **no** crash and that the impact cases do; report the false-positive and false-negative counts on the fixture set.

Done when: a cushioned drop test raises the coach alert with the right pin within a few seconds, a lap with hard braking and kerb strikes raises none, and the coach banner, sound, acknowledgement and audit entry all work.

---

## Phase 2.3 — Coaching features (software only; can run alongside 2.1 and 2.2)
Branch: `phase2-3-coaching`. Follows Workstream C of the existing brief: session notes return (API exists), session goals using `goal_text` / `goal_passed`, rule-table guidance in one tested file, personal trend graph, career graph after 5 sessions, **sector split timing** from GPS split lines drawn on the map (replaces the Phase 2 note in the corner-deltas panel), trait-based driving-style badges, an opt-in consistency leaderboard (never raw speed; Performance Mode only; opt-out any time) and Coach/Admin cross-driver comparison without biometrics.

Additions: every rule and badge is deterministic, explained on screen in one sentence, and covered by a test; "machine learning" is limited to documented statistics (for example spread of corner times) until enough real labelled sessions exist.

Done when: each item replaces its banner, and the access sweep proves drivers cannot see other drivers' data except through the opt-in leaderboard.

---

## Phase 2.4 — Glove v2: vibration, heartbeat, self-test (FIRMWARE, owner approval first)
Branch: `phase2-4-glove-v2`. Hardware: haptic driver + coin motor (Part A).

0. **Design note first** (`firmware/docs/GLOVE_V2.md`): wiring, pins (check boot-strapping and input-only pins before assigning), power, protocol v2, failure behaviour. Stop until the owner approves.
1. **Protocol v2** in the shared header: version 2, a message type byte (`STAGE`, `HEARTBEAT`, `SELF_TEST_REQUEST`, `SELF_TEST_RESULT`), same encryption, replay counter and sender check. Both boards are reflashed together; v1 packets are rejected after the upgrade (state this in the README). Host tests for every new type and every rejection path.
2. **Vibration:** pattern per stage (NOMINAL none, MONITORING short pulse, INTERVENE repeated pulses), timing at or below 3 per second, intensity setting, and a hard limit on continuous on-time. Through a haptic driver IC, or if a transistor drives the motor directly: flyback diode across the motor **[required]**. Vibration stops when the glove falls back to WAITING.
3. **Glove heartbeat:** every 2 s the glove sends `HEARTBEAT` (firmware version, battery millivolts if measured) to the bridge; the bridge writes a new output line to USB (the input format `g,STAGE` stays unchanged); Connect bridge forwards it as a `heartbeat` event, so the Admin grid shows the glove online.
4. **Remote self-test:** the parked Admin "Run Diagnostic" creates a `DeviceCommand`; Connect bridge picks it up and sends a self-test request; the glove runs an LED and motor check and replies; the result closes the command. Remove the Phase 2 banner.
5. **Watchdog and brownout:** task watchdog with a stated timeout, brownout detection, reset reason printed at start-up.

Done when: stages light and buzz with correct patterns, the glove shows online in the Admin grid, a self-test round-trip completes, and every host test passes.

---

## Phase 2.5 — Kart sensor unit (FIRMWARE, owner approval first)
Branch: `phase2-5-kart-unit`. Hardware: Part A kart unit.

0. **Design note first** (`firmware/docs/KART_UNIT.md`) with a wiring table, pin checks, a power budget table (component, active current, sleep current, duty cycle, average contribution; regulator quiescent current; 20–30% margin; every figure from datasheets, tagged), and the mounting plan. Stop until approved.
1. **Sensing:** motion sensor (orientation and linear acceleration) at a stated rate, a high-g accelerometer for impacts, GPS at its highest stable update rate. Validate every reading (range, NaN, bus timeouts; I2C bus recovery after a stuck line).
2. **On-board stage:** zone detection from the map's corner positions (downloaded once per session as a compact profile), lateral g from speed × yaw rate cross-checked with the accelerometer, stage by the existing rule, sent to the glove over ESP-NOW (protocol v2) at a fixed rate. The glove's allowed-sender list now holds the bridge and this unit.
3. **Crash detection:** the same state machine and settings file as 2.2, with the high-g accelerometer for impacts; events to the server through the events endpoint.
4. **Link to the server:** through a phone hotspot (Wi-Fi) as primary; offline flash ring buffer (bounded, wear-levelled) when out of range, flushed in order with device times. Each unit has its own revocable device token stored in protected NVS, never in code.
5. **Fallback:** the laptop + bridge path keeps working unchanged.
6. **Measurements to report:** corner-to-LED delay (method: timestamped serial logs on both boards against a common reference), ESP-NOW range on the track, GPS fix quality, battery life over a session.

Done when: a lap with no laptop near the track lights and buzzes the glove, the coach screen shows the run when signal allows, and the measurements are written down.

---

## Phase 2.6 — Biometrics
Branch: `phase2-6-biometrics`. Hardware: Part A biometrics.

1. **Heart rate:** a chest strap using the standard Bluetooth Heart Rate Service, read by the kart unit (BLE central) or by the phone page (Web Bluetooth works in Chrome on Android only **[Verified]**), posted as `BiometricReading` with the driver's consent recorded.
2. **SpO2 and breathing:** wrist and finger optical sensors are unreliable under kart vibration **[Assumption — if wrong, readings would be usable during driving; verify with recorded data]**. Treat SpO2 as a pit-lane spot check only, and breathing rate as experimental until validated.
3. Live cards on the coach screen only (never shared), replacing "No sensor connected".
4. **Stress level** High / Mid / Low as a documented deviation from the driver's own baseline; a learned model only after enough labelled sessions.
5. Post-session note when high stress coincides with rising alerts. Every biometric screen says "training aid, not a medical device".

---

## Phase 2.7 — Alert video clips (Phase 1.5 item)
Branch: `phase2-7-alert-clips`. Hardware: action camera or phone camera (Part A).

The ESP32 cannot record a useful rolling video buffer **[Assumption — a camera module on the ESP32 is too limited in resolution and memory for this]**, so: record with a camera on the kart or helmet; after the session the coach uploads the video; the app aligns it to the session by a clap or flash marker or by the camera's timestamp with a manual offset; the server cuts a 10-second clip around each alert (tool in a container, limits on file type and size, no shell built from user input); clips appear on the Driver and Coach session screens behind the existing permissions. Retention follows the 2.0 setting.

---

## Phase 2.8 — Pilot gate (before any academy trial)
Branch: `phase2-8-pilot-gate`.

- Field-test report: radio range, battery life, corner-to-LED delay, calibration drift, crash-detection fixture results, what the app showed against what the driver felt.
- Firmware: flash encryption and secure boot plan for both boards, key rotation and revocation steps.
- Backend: concurrency tests on PostgreSQL for the row-locking code; hosting on `docker-compose.yml` (Caddy + Postgres + Redis) with backups tested by a restore; a simple load test.
- Safety and consent: academy sign-off, consent (and parental consent for under-18 drivers), retention settings set, enclosure and mounting reviewed (vibration, water, heat), LiPo charging rules written.

---

## Part A — Recommended hardware (nothing bought yet)

Prototype-grade parts, chosen for availability in India and support for the Arduino core. Prices are **[Estimate — check at purchase]**; ratings are **[Verify vs. Datasheet]**.

| Item | Recommended | Why | Instead of (in the old brief) |
|---|---|---|---|
| Kart unit MCU | ESP32 dev board with external antenna (ESP32-WROOM-32U + 2.4 GHz antenna) | Same family as the glove and bridge; external antenna for range on a track | — |
| Motion sensor | BNO085 breakout (on-chip fusion: orientation and linear acceleration) | Removes gravity correctly when the kart tilts; less maths on the ESP32 | MPU-9250 (discontinued **[Verify]**) |
| Impact sensor | ADXL375 breakout (high-g accelerometer, about ±200 g **[Verify vs. Datasheet]**) | Normal IMUs saturate at ±16 g or less during an impact | — |
| GPS | u-blox NEO-M8N module with active antenna (up to about 10 Hz **[Verify vs. Datasheet]**) | Faster updates than NEO-6M (about 5 Hz maximum **[Verify]**) for corner timing | NEO-6M |
| Glove vibration | DRV2605L haptic driver + 10 mm coin vibration motor (ERM) | Patterns, braking and protection built in | Bare motor on a GPIO (never drive a motor from a pin) |
| LED data level | 74AHCT125 level shifter (3.3 V → 5 V data) | ESP32 output is 3.3 V **[Verified]**; WS2812B at 5 V may misread it under vibration | — |
| Heart rate | BLE chest strap with standard Heart Rate Service (for example Coospo or Polar) | Chest ECG straps tolerate motion far better than optical sensors | MAX30102 on a strap |
| SpO2 (pit only) | MAX30102 module | Spot checks at rest | — |
| Power (kart unit, glove) | 1S LiPo with protection, charger with protection (TP4056 board with DW01), suitable regulator | Portable; protection against over-discharge | — |
| Video | Action camera or a phone on a mount | Proper rolling recording | ESP32 camera |
| Decoupling | 100 nF at each board and sensor, 470–1000 µF across the LED strip supply | Stable supply under motor and LED load | — |

Approximate total for one kart unit, one glove upgrade and one chest strap: **₹9,000 – ₹16,000 [Estimate]**, dominated by the motion sensor, GPS and strap.

⚠ **Safety:** LiPo cells can catch fire if crushed, punctured or charged without protection; charge them off the kart and never unattended. Fuse the battery lead. Keep the kart unit mount clear of the driver's controls. Never drive a motor or a strip directly from an ESP32 pin.

## Part B — What I changed from the existing brief, and why

1. **Impact sensing:** the brief's MPU6050/9250 saturates at ±16 g, so it cannot measure a real impact; added a high-g accelerometer and made saturation count as impact evidence.
2. **GPS:** NEO-6M updates too slowly for corner timing at kart speeds; recommended NEO-M8N.
3. **Biometrics:** the brief assumed a MAX30102 strap; optical sensors are unreliable while driving, so heart rate moves to a BLE chest strap and SpO2 to pit checks.
4. **Crash events:** added idempotent event IDs (so retries never duplicate an alert), a browser sound-permission step (browsers block sound until a click), repeat sound until acknowledged, and an offline-track fallback.
5. **Missing items added:** glove heartbeat and online status, remote self-test, alert video clips, retention and consent, the Phase 1 loose ends, watchdogs, measurement of delay and range, and a pilot gate.

## Part C — Decisions you need to make

1. **[Assumption] Maturity stage:** I assumed Phase 2 is a **Prototype** (bench and slow test runs), with Phase 2.8 as the gate to a **Pilot** at an academy. If you want to go straight to a Pilot, enclosures, battery safety, consent and the field-test report move to the start.
2. Android or iPhone for the phone unit (Web Bluetooth only works on Android Chrome).
3. Approve firmware work for 2.4 and 2.5 (yes / later).
4. Delete rule for users (keep permanent delete, or go back to deactivate only), which decides `TC-ADMIN-07`.
5. Mobile signal at the track, or a trackside laptop with its own Wi-Fi.
6. Leaderboard metric (spread of lap times, or alerts per lap).
