# Phase 2 — Repo survey (Phase 2.0, task 0)

Branch `phase2-0-groundwork`, cut from `phase2-software` (= `main` at `f54ab68`
plus the master prompt). Plan: `Trackside_Handoff_Package/trackside_handoff/PHASE2_MASTER_PROMPT.md`.
Paths below are relative to `trackside/`.

## Contradictions and open points (stop-and-report items)

| # | Prompt says | Code says | Proposed resolution |
|---|---|---|---|
| C1 | 2.1: "Session mode set by the Coach to `simulator` or `phone`" | `Session.mode` already means Safety / Performance (`backend/driving_sessions/models/session.py`) and drives the default limits | Add a **separate** field, `data_source` (`simulator` / `phone` / `kart_unit`), and leave `mode` alone |
| C2 | 2.0 task 1c: "port the corner-time fix" if it is not on `main` | No such fix exists on any branch (`main`, `custom-maps`, `claude/research-project-8vh0z1`). `corner_deltas.py` still groups by `(zone, lap_number)` | Nothing to port. Write the fix fresh (time each corner crossing) with tests, or drop the task. **Owner decides** |
| C3 | 2.0 task 2: glove events arrive "via bridge" with a device token | The bridge has no network. Its data reaches the server only through the browser's Connect bridge, signed in as a Coach | Allow a signed-in **Coach** to forward events for devices assigned in their academy, in addition to device tokens and the Driver's own phone |
| C4 | 2.0 task 3: "scheduled purge command" | No scheduler in either deployment (Render free plan; `docker-compose.yml` has no cron) | Ship `manage.py purge_expired_data` (dry-run by default) and document running it from host cron or a Render cron job |
| C5 | 2.0 task 1a: `TC-ADMIN-07` | `e2e/test_admin.py:142` asserts no Delete button; permanent delete with typed confirmation exists | Owner answered "keep the permanent delete": rewrite the test to check the typed confirmation |

## Phase 2.0 — Groundwork

| Item | Exists | Missing | Files to touch |
|---|---|---|---|
| Selenium waits | `e2e/pages/base_page.py` `is_visible(timeout=3)` and other 3 s waits; `requests` calls use `timeout=5` throughout `e2e/*.py` | One shared setting (10 s UI, 15 s API, env override) | new `e2e/timeouts.py`; `e2e/pages/*.py`; `e2e/conftest.py`; `e2e/setup_helpers.py`; `e2e/test_*.py` |
| Device events | `Device` (with `api_key_hash`, `last_seen_at`), `DeviceTokenAuthentication` (`backend/devices/authentication.py`), `DeviceCommand` | `DeviceEvent` model, `POST /api/devices/events/`, per-type payload schemas, idempotency on `event_id`, throttle, access-sweep entry | `backend/devices/models.py` (or new `models_events.py`), new `views_events.py`, `event_schemas.py`, `urls.py`, `throttles`, migration, tests; `accounts/tests/test_access_sweep.py` |
| Retention and consent | Nothing | Academy settings (single row), purge command, per-driver `consent_recorded` and `under_18` flags, refusal when consent is missing | `backend/accounts` (driver flags + admin API) or a new `academy` app; management command; admin screen in `frontend/src/pages/admin/` |
| Time fields | `Telemetry.recorded_at` and `BiometricReading.recorded_at` only | Device time, sequence number and server receive time on **new** device payloads (events now, phone readings in 2.1) | `DeviceEvent` fields; docs table of which time each screen shows |

## Phase 2.1 — Phone as kart unit

- Exists: telemetry ingest `POST /api/sessions/<id>/telemetry/` (session or device-token auth, batch ≤ 100, range checks, row lock, alerts, WebSocket `telemetry_reading` / `alert_triggered`); access helpers in `driving_sessions/access.py`; live map (`frontend/src/components/ui/live-track/`); Connect bridge (`frontend/src/lib/bridge-serial.ts`).
- Missing: `data_source` field (C1), Driver-only phone page, calibration, lateral-g and position maths, offline queue, recorded fixtures.

## Phase 2.2 — Crash detection

- Exists: `AuditLogEntry` (add actions for acknowledgement), WebSocket groups per session, live map pins.
- Missing: detector state machine and shared settings file, `crash_suspected` / `lost_contact` handling on top of `DeviceEvent`, coach banner + sound + acknowledge, driver "I'm OK", crash list, fixtures, simulator `crash` scenario.

## Phase 2.3 — Coaching

- Exists: `SessionNote` API (`views_notes.py`) and `use-coach-notes.ts` hook, screen parked behind a banner in `pages/coach/index.tsx`; `Session.goal_text` / `goal_passed`; corner deltas and best lap; driver panels in `pages/driver/components/`.
- Missing: rule-table guidance, trend and career graphs, sector splits (note in `corner-deltas-panel.tsx`), badges, opt-in leaderboard, cross-driver comparison.

## Phases 2.4 to 2.8 (hardware or field work; software parts only)

- 2.4: `DeviceCommand` self-test endpoints exist (`devices/urls.py`: commands, pending, complete); admin "Run Diagnostic" parked in `pages/admin/index.tsx`. Firmware gated.
- 2.5: Firmware gated. Server side reuses telemetry ingest, device tokens and `DeviceEvent`.
- 2.6: `BiometricReading` + `views_biometrics.py` + WebSocket `biometric_reading` exist; `biometrics-cards.tsx` shows "No sensor connected".
- 2.7: Nothing exists.
- 2.8: `docker-compose.yml` production stack exists; no load or restore test.

## Small things noticed (not fixed in 2.0 unless asked)

- `Device.Status.CONNECTED = "connected"` is assigned after the class body (`devices/models.py:106`), so it is not a valid choice; migration `0004` already moved stored rows to `offline`. Harmless today; worth removing when the events work touches this file.
