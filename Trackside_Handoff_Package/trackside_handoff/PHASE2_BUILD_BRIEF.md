# Trackside — Phase 2 Build Brief

Phase 1 is built: the web app (`trackside/`), the simulator (`trackside/demo/`),
the glove and bridge firmware (`trackside/firmware/`), drawn and imported GPS
maps, and the hosted demo. Phase 2 turns the demo into something that runs on a
real kart and fills in the coaching features the proposal promised but Phase 1
parked behind the yellow "Development Ongoing" banner.

Give section 1 to the coding agent. Sections 2 to 4 are reference.

---

## 1. Build Prompt (give this to the coding agent first)

You are extending **Trackside**, an existing Django + DRF + Channels backend and
React 19 + Vite + Tailwind frontend in `trackside/`. Read `trackside/README.md`,
`backend/README.md`, `frontend/README.md`, `demo/README.md` and
`firmware/README.md` before changing anything. Extend what exists; do not
rewrite or replace working Phase 1 code.

### Rules carried over from Phase 1 (non-negotiable)
- No file over 300 lines. Split by feature, not by file type.
- Every function and component has a short simple-English comment saying what
  it does and why.
- Descriptive names; no single letters or unexplained abbreviations.
- Default-deny API: every new endpoint has explicit permission classes, an
  ownership check (no IDOR), input validation, and is added to the route access
  sweep test (`accounts/tests/test_access_sweep.py`).
- Django ORM only, no raw SQL. No `dangerouslySetInnerHTML`.
- No secrets, API keys or passwords in code, commits, logs or command lines.
- Every feature ships with tests. The full backend suite, `vitest`, the demo
  `pytest` suite and `VITE_ENABLE_DEMO_TOOLS=true npm run build` must all pass
  before a commit.

### Hard limits (do not change without the project owner's written approval)
- **Firmware** under `trackside/firmware/` is not touched unless the owner
  approves that specific change. Workstream B below needs that approval first.
- The serial line format `g,STAGE` and the stage rule (NOMINAL / MONITORING /
  INTERVENE against the corner limit) stay exactly as they are.
- LED and vibration flash rates stay at or below 3 per second
  (photosensitivity).
- Biometric values never appear on any shared or cross-driver view. The
  leaderboard and badges never expose raw biometrics or raw speed.

### Build in this order. Finish and verify each workstream before the next.

#### Workstream A — Phone as a temporary kart unit (no firmware)
Goal: real motion and position data from a phone mounted in the kart, before
the kart unit hardware exists.
1. **Ingest endpoint.** A signed-in Driver can post readings to their own
   active session only. Rate-limited, batched (several readings per request),
   validated ranges (lateral g 0–10, speed 0–200 km/h, lat/lng valid). Reuse
   the existing telemetry and alert pipeline so the coach screen, corner
   detection and alerts work unchanged.
2. **Phone Sensor page** (Driver role, after sign-in, never on the login
   page). Start/Stop button that asks for motion and location permission (iOS
   needs a tap), keeps the screen awake (Wake Lock), and shows connection,
   GPS accuracy and readings per second.
3. **Calibration step.** "Hold still" then "drive straight" to find which
   phone axis is sideways. Store the result per session.
4. **Lateral g.** Primary: `speed × yaw rate ÷ 9.81` (gyroscope yaw rate,
   GPS speed). Cross-check against the accelerometer's sideways reading and
   flag the session if they disagree for more than a few seconds (phone moved
   in its mount).
5. **Smooth dot.** Between 1 Hz GPS fixes, advance the position along the
   track outline by speed and snap to the nearest outline point; correct on
   each new fix.
6. **Session mode setting.** Coach chooses Simulator or Phone per session, so
   a stray phone cannot feed a simulator run.
7. **Recorded-data tests.** Save a few real phone recordings as test fixtures
   and test the g and position maths against them, so changes do not need a
   kart.

Done when: one slow real kart run shows the live dot and corner alerts on the
coach screen, and the laptop's Connect bridge drives the glove from phone data.

#### Workstream B — Real kart hardware (FIRMWARE APPROVAL REQUIRED FIRST)
Write a short design note and get the owner's approval before any code.
1. **Kart unit:** ESP32 + IMU (MPU6050/9250) + GPS (NEO-6M/M8N), computing
   lateral g and stage on board.
2. **Kart-to-glove link on the kart** (about 1 m, ESP-NOW), so the glove keeps
   working anywhere on the track without a laptop in range.
3. **Kart-to-server link** for the coach screen, through a phone hotspot or
   the phone page relaying over Bluetooth (Web Bluetooth is Chrome on Android
   only).
4. **Vibration motor** on the glove (the proposal's primary alert channel),
   same stages as the LEDs.
5. **Device authentication:** each board gets its own revocable device token;
   no shared passwords. Activate the parked admin "Run Diagnostic" using the
   existing `devices` command endpoints.
6. Keep the laptop + bridge path working as a fallback.

Done when: a lap with no laptop near the track still lights and buzzes the
glove, and the coach screen shows the run when signal allows.

#### Workstream C — Coaching features from the proposal
All are deterministic rules over the data already stored. No AI-generated
advice in this phase.
1. **Session notes return:** coach notes tied to a lap and a corner (the API
   exists; rebuild the recorder screen and remove its Phase 2 banner).
2. **Session goals:** set before a session (for example "zero INTERVENE at the
   hairpin"), pass/fail summary at the end. Fields `goal_text` and
   `goal_passed` exist on `Session`.
3. **Plain-language guidance:** rule table mapping alert patterns to tips,
   such as repeated INTERVENE in one corner → "brake earlier into Turn 3";
   frequent MONITORING with no INTERVENE → "room to carry more speed here".
   The rule table lives in one file with tests for every rule.
4. **Personal trend graph:** alerts per lap over time for the driver's weakest
   corner.
5. **Career graph:** overall trend across all sessions; unlocks after 5
   sessions, with a progress placeholder before that.
6. **Sector split timing:** GPS split lines on the track, sector times per lap
   (replaces the note in the corner-deltas panel).
7. **Driving-style badge:** trait-based (consistency, braking timing) from the
   driver's own corner data; visible only inside the academy.
8. **Opt-in leaderboard:** consistency-based, never raw speed; Performance
   Mode sessions only; driver opts in and can opt out at any time; academy
   members only.
9. **Cross-driver analytics (Coach/Admin):** corner-by-corner comparison and
   admin usage reports, with no biometric values.

Done when: each item replaces its Phase 2 banner, and the access sweep proves
drivers cannot see other drivers' data except through the opt-in leaderboard.

#### Workstream D — Biometrics (needs the strap hardware)
1. Biometric strap (MAX30102 heart rate and SpO2, plus a breathing sensor)
   posting through the same device authentication as Workstream B.
2. Live cards on the coach screen replace the "No sensor connected" text.
3. **Stress level High / Mid / Low** compared with the driver's own baseline.
   Start with a documented rule (deviation from personal baseline); a learned
   model only once enough labelled sessions exist.
4. **Post-session note** when high stress coincides with rising alerts later
   in the session.
5. Label all biometric output "training aid, not a medical device".

Done when: a real strap shows live values on the coach screen only, and the
stress label is tested against recorded readings.

### Out of scope for Phase 2
- Phase 1.5 alert video clips (separate brief; needs camera hardware).
- Predictive alerts (warning before a mistake happens).
- AI-generated reports and coaching advice.
- Native iPhone or Android apps (web pages only).
- Multi-academy or public use.

---

## 2. Definition of done for Phase 2
- Workstreams A and C complete and verified; B and D complete if their
  hardware is available, otherwise left behind banners with a written status.
- At least one recorded real kart session stored and replayable.
- A short field-test report: radio range, battery life, phone calibration
  drift, and what the app said against what the driver felt.
- All Phase 1 tests still pass; no Phase 1 feature removed.

## 3. Safety and privacy
- Trackside is a coaching aid, not a safety system. When data stops, the glove
  shows its waiting light (one dim blue LED); the academy decides what a driver
  does then.
- Ask the academy for consent rules if any driver is under 18, and for how long
  session and biometric data is kept. Add a retention setting.
- Production hosting uses `docker-compose.yml` (Caddy + backend + Postgres +
  Redis) with backups; the free Render plan is for demos only.

## 4. Open questions for the project owner
1. Which phone will be mounted in the kart: Android or iPhone?
2. Approve firmware work for Workstream B (yes / no / later)?
3. Which biometric strap and breathing sensor will be bought?
4. Leaderboard metric: which consistency measure (for example lap-time spread,
   or alerts per lap)?
5. Is there mobile signal across the whole track, or should the stack run on a
   trackside laptop with its own Wi-Fi?
