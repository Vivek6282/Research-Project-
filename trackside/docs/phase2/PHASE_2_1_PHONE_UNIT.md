# Phase 2.1 — The phone as a temporary kart unit

## How to use it

1. **Admin:** record the driver's consent (`PATCH /api/academy/drivers/<id>/consent/` with
   `{"consent_recorded": true}`; there is no admin screen for it yet).
2. **Coach:** *Maps & Demo* tab → **Real-time session (phone)** → choose the driver and a map with a GPS
   outline (imported or drawn; the schematic Demo Circuit cannot be used) → **Start real-time session**.
3. **Driver, on the phone fixed in the kart:** sign in, press **Phone sensor**, then **Start sensors**
   (allow motion and location). Calibrate:
   - **Step 1:** kart still, phone firmly mounted → **Hold still and calibrate** (2.5 s).
   - **Step 2:** drive straight and speed up firmly; it finishes by itself. **Skip** sends readings without
     the accelerometer cross-check.
4. Keep the page open with the screen on. The coach sees the live dot, corners, laps, g and
   **GPS ±N m**. The laptop's **Connect bridge** passes the stage on to the glove as before.
5. **Stop**, then **Save sensor recording** to keep the raw data as a test file. **Finish** in the coach
   panel ends the session.

The page needs HTTPS (the Render site has it). iPhones ask for motion permission after the tap.

## How it works

| Part | Where |
|---|---|
| Up and forward from calibration | `frontend/src/lib/phone-sensors/calibration.ts` |
| Sideways g = speed (m/s) × turn rate (rad/s) ÷ 9.81, turn rate about the calibrated "up" | `lateral-g.ts` |
| Cross-check with the accelerometer; warning after 3 s of disagreement above 0.35 g while moving | `lateral-g.ts` (`DisagreementWatch`) |
| Phone moved in its mount: gravity more than 20° from calibration for 2 s (hard cornering and braking are ignored) | `lateral-g.ts` (`MountWatch`) |
| Smooth position between 1 Hz GPS fixes: along the outline by speed × time, snapped at each fix | `track-follower.ts` |
| Offline queue: up to 3,000 readings, oldest dropped first (counted), sent in order 100 at a time with growing retry delays | `upload-queue.ts` |
| One run (calibration steps, a reading every 100 ms) | `frontend/src/pages/driver/phone/phone-run.ts` |
| Corner and lap decided by the **server** from GPS, never by the phone | `backend/driving_sessions/phone_placement.py` |
| Phone readings need consent and a real-time session (403 / 409) | `backend/driving_sessions/phone_rules.py` |
| Calibration and warnings stored on the session | `PUT /api/sessions/<id>/phone-calibration/` |

New fields: `Session.data_source` (`simulator` / `real_time`; only a coach or admin sets real time),
`Session.phone_calibration`, `Session.sensor_flags`; `Telemetry.sequence`, `Telemetry.received_at` (server time,
set for every reading), `Telemetry.gps_accuracy_m`.

## Verified

- Backend tests for placement, laps across the start/finish line, consent, simulator sessions, the
  calibration endpoint and who may set real time (`driving_sessions/tests/test_phone_unit.py`).
- Frontend tests with **SYNTHETIC** sensor data (a phone tilted 60° and turned 30°, a 20 m circle at 15 m/s):
  calibration, 1.147 g from both methods, warnings, the follower, the queue, the run and both screens.
- In Chromium with simulated GPS and motion: coach started the session, the phone calibrated and sent 505
  readings over one and a half laps with none dropped or refused; the server placed them in all four
  corners (including one across the start/finish line), counted laps 1 and 2, and raised alerts; the
  coach screen showed `GPS ±4 m`; the recording file downloaded.

## Not done (needs you)

- **Real phone recordings** as test fixtures: use **Save sensor recording** on a real run and add the files.
- **A slow real kart run** (the phase's "done when"), and checking that the glove follows through Connect
  bridge with phone data.
- Admin screen for consent (API only).
