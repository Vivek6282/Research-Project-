# Trackside: working agreement

## Project
IoT karting safety and coaching system (MCA research project). A glove with LEDs
and a vibration motor warns the driver per corner. A web app serves Admin, Coach
and Driver. Stack: Django + DRF + Channels, React + Vite + Tailwind, PostgreSQL
in production, ESP32 firmware in Arduino. The owner is a beginner with hardware.
Phase 1 = rule-based system, no ML. Phase 1.5 (alert video clips) and Phase 2
(ML/analytics) are NOT started: do not build them unless asked.

## How to work (most important)
1. Verify by running things. Reading code or a passing single test is not
   verification. Never say "done" or "should work" without running the checks.
2. Test on a fresh, empty database, never on an existing dev database.
3. Before saying done, run all of these and quote the real numbers:
   python manage.py test, pytest, npm run build, and the Selenium suite when
   the UI changed. manage.py test and pytest must find the same number of tests.
4. Never weaken, skip or delete a test to make it pass. Fix the app or the test
   setup. If a test is flaky, fix the wait, do not remove it.
5. Do only what was asked. If you find another problem, report it. Do not fix it
   silently. A typo on the line you are already editing is the only exception.
6. Do not re-open the settled decisions below.

## Review habits (look for these in your own work and in existing code)
- A value computed and then never used.
- A hardcoded fallback that silently replaces real data.
- An empty except/catch that hides a failure.
- A button or input with no working handler.
- Mock data without a visible label.
- A stale CSRF token reused after login.
- Docs or docker-compose naming an env var that settings never reads.
- A commit message that claims more than the diff does. Read the diff.
- Layout: with a real browser, check document.documentElement.scrollWidth <=
  window.innerWidth at 375, 768 and 1440 px on all three dashboards. Screenshots
  alone miss sideways overflow.

## Settled decisions
- Single Admin account, no public sign-up. Admin creates all Coach and Driver
  accounts and sets their passwords. Login by email or generated ID (TRK-DRV-######).
- Users are deactivated, never hard-deleted (Session.driver cascades and would
  destroy history).
- Dark theme only. No theme toggle. Font size presets stay.
- Drivers see only their own data. Every query is scoped by ownership.
- Thresholds are per corner. A custom threshold is never above the zone default,
  and changes are insert-only (history kept). Sprint-kart range is 1.0 to 1.5 g.
- Signal strip: 5 segments (green, green, amber, amber, red). Lit counts 2 / 4 / 5
  for Nominal / Monitoring / Intervene, all from one shared getTrajectoryStage.
- Login rate limit is 5/min in settings, unconditionally. Only the e2e server may
  get a higher value, via the LOGIN_THROTTLE_RATE environment variable.
- One deployment per academy (single tenant). PWA, not a native app.

## Tests
- Backend tests are APITestCase classes. Every tests/ folder has __init__.py.
- The Selenium suite must create all its own data on an empty database.

## Hardware facts
- Glove ESP32 address B0:CB:D8:0A:4F:20. Bridge ESP32 address B0:CB:D8:0A:95:64.
- Glove pins: LED strip data GPIO 18, motor GPIO 26. ESP32 Arduino core 3.3.x.
- Bridge serial line format: "1.25" or "1.25,MONITORING". Without a stage it uses
  a fixed 1.15 g limit.
- Do not change firmware logic or pins without asking. Firmware cannot be compiled
  here, so say plainly that it was not compiled or run on hardware.

## Environment (Windows)
- Use py, not python. The demo reads SERIAL_PORT from trackside/demo/.env.
- The Arduino Serial Monitor must be closed before the simulator runs
  (one program per COM port).
- The project folder is inside OneDrive, which can interfere with installs.

## Git
- One commit per task, starting with the task or defect ID. Do not push unless told.
- Never commit .env files, tokens, keys or database files.

## Reporting (end of every task)
1. Files changed, one line each.
2. Commands run, with exact pass/fail counts.
3. What you could NOT verify, and why.
4. Anything wrong you noticed but did not change.
Write "verified" or "not verified". Never "should work".

## Communication
Short and plain. Explain jargon in one line. For anything physical (wires, ports,
buttons), give exact click-by-click or command-by-command steps.
