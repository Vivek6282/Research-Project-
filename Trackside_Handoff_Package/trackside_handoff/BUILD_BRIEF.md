# Trackside — Build Handoff Package

This package contains everything finalized for Phase 1 of Trackside, an IoT-based
karting driver safety and performance system. Hand this whole folder to Claude
Code (or another agentic coding tool) to begin the actual build.

---

## 1. Build Prompt (give this to the coding agent first)

Build a full-stack web application called **Trackside**, a role-based karting
driver safety and performance coaching platform for a single karting academy
(intradomain — no public self-registration).

### Tech stack (use exactly this, no substitutions)
- Frontend: React, styled with Tailwind CSS and shadcn/ui components
- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Device communication (mocked for now, real integration later): ESP-NOW/BLE
  data arriving via a REST/WebSocket endpoint

### Code quality requirements (non-negotiable)
- No file may exceed 300 lines — split into smaller files/functions/components
  as needed
- Every function/component needs a simple-English comment explaining what it
  does and why, written for a reader with moderate technical background
- Variable and function names must be descriptive and unambiguous — no
  single-letter names, no unexplained abbreviations
- Organize code by feature/module, not by file type dump — e.g. `driver/`,
  `coach/`, `admin/`, `auth/`, not one giant `components/` folder

### Security requirements (must be explicitly implemented and testable, not
just assumed)
- No SQL injection — use Django ORM exclusively, never raw string-interpolated
  SQL
- No XSS — never use `dangerouslySetInnerHTML`; rely on React's default
  escaping
- No IDOR — every API endpoint must verify server-side that the requesting
  user owns the record being accessed (e.g. a Driver cannot fetch another
  driver's session by changing an ID)
- No authentication bypass — every protected endpoint checks role
  server-side, not just hidden in the frontend
- No insecure deserialization — API only accepts/returns JSON via DRF
  serializers, never raw pickle
- No SSRF — do not build any endpoint that fetches an arbitrary
  user-supplied URL
- No race conditions — use database transactions for any concurrent writes
  (e.g. alert logging)
- Passwords hashed via Django's built-in PBKDF2, never stored or logged in
  plain text
- Rate-limit the login endpoint against brute force
- HTTPS and environment-variable secrets assumed in deployment; never
  hardcode credentials

### Authentication model
- Single Admin account (seeded, not self-registered) creates all Coach and
  Driver accounts
- No public sign-up page — login screen only
- Three roles: Admin, Coach, Driver — each redirected to their own dashboard
  after login, with server-side role enforcement on every API call

### Database schema — implement exactly these Phase 1 tables
(PostgreSQL, UUID primary keys — full detail in `Database_Schema_Design.docx`)

- `users` (id, name, email, password_hash, role enum[admin/coach/driver],
  is_active, created_at, created_by)
- `user_preferences` (user_id, theme enum[dark/light], font_size
  enum[small/medium/large/xlarge])
- `tracks` (id, name, reference_line jsonb, kart_class
  enum[rental/sprint], surveyed_at, created_by)
- `zones` (id, track_id, label, threshold_g float, gps_range jsonb)
- `driver_zone_thresholds` (id, driver_id, zone_id, custom_threshold_g
  float — must be ≤ zones.threshold_g, set_by, updated_at — **insert-only,
  never update in place**)
- `sessions` (id, driver_id, track_id, mode enum[safety/performance],
  goal_text, goal_passed, started_at, ended_at)
- `telemetry` (id, session_id, zone_id nullable, recorded_at, lateral_g,
  speed_kmh, gps_lat, gps_lng — composite index on session_id+recorded_at)
- `alerts` (id, session_id, zone_id, severity enum[amber/red], g_value,
  threshold_applied float, triggered_at)
- `biometric_readings` (id, session_id, recorded_at, heart_rate, spo2,
  breathing_rate)
- `session_notes` (id, session_id, coach_id, zone_id nullable, note_text,
  created_at)
- `devices` (id, device_type enum[glove/kart_unit/biometric_strap],
  assigned_to, status enum[connected/pairing/offline], last_seen_at)

### UI design system
Dark/light theme toggle (server-stored preference, not just localStorage),
4 fixed font-size presets (no free slider). Palette: near-black `#0A0E13`
background, panels `#12181F`/`#161D26`, text `#E7EDF3`, muted `#7C8898`,
accent blue `#3FA6E0`. Status colors: green `#33D17E`, amber `#F2A93B`, red
`#E5473C`, shown together as a repeating 5-segment "signal strip" component
(mirrors the physical glove LEDs). Reserve a distinct yellow `#E8C547`
exclusively for "Development Ongoing" banners — never used elsewhere. Top
bar: logo top-left, avatar dropdown top-right (Settings, Log Out).
Dismissible first-login tutorial per role. Fully responsive down to mobile.

Reference implementation of this visual language: `TracksideApp.jsx` and
`KartingSystem.jsx` (interactive demos, not production code — rebuild
properly against the real schema and multi-file structure above rather than
copying these files directly).

### Build these three role-based dashboards, all functional against the
real schema above

**Coach:** driver roster, live session view (speed/g-force chart, signal
strip, biometric cards), customizable per-driver per-zone threshold control
(validated server-side to never exceed the zone default), session notes
tied to a lap/zone, raw historical session list.

**Admin:** user management (create/edit/deactivate Coach and Driver
accounts), device connectivity status, raw usage/session-count summary.

**Driver:** session mode selector (Safety/Performance), zone-by-zone raw
alert counts, best-lap raw breakdown, session goal pass/fail, personal
baseline comparison against their own past sessions only (never other
drivers).

### Explicitly out of scope for this build
Implement as visibly disabled sections with a "Development Ongoing" banner
(using the yellow accent defined above) and static mock data, not
functional:

- **Phase 1.5:** automatic alert video clips (rolling-buffer camera capture
  synced to alert timestamps)
- **Phase 2:** plain-language coaching guidance, personal/career trend
  graphs, driving-style badges, opt-in leaderboard, cross-driver analytics,
  biometric stress classification (High/Mid/Low)

Each "Development Ongoing" section should be clearly non-interactive
(disabled controls, muted/faded content) so it's obvious to a reviewer that
it's a placeholder, not a bug.

---

## 2. Supporting Documents in This Package

| File | What it's for |
|---|---|
| `Trackside_Project_Proposal.docx` | Full project proposal — problem statement, objectives, all module features, IoT hardware, tech stack, security, architecture |
| `Database_Schema_Design.docx` | Complete Phase 1 schema reference with example data for every table |
| `Project_Synopsis_Phase1.docx` | Plain-language summary of Phase 1, for anyone non-technical |
| `Feasibility_Analysis.docx` | Technical/operational/economic feasibility study |
| `Literature_Review_Phase1.docx` | Academic literature review with 14 real references |
| `Requirement_Gathering_Manager_Interview.docx` | Stakeholder interview used to justify feature priorities |
| `TracksideApp.jsx` | Interactive demo — all 3 role dashboards, Phase 1 core functional, Phase 1.5/2 marked with dev-ongoing banners |
| `KartingSystem.jsx` | Earlier demo — Coach/Admin dashboards, simulated telemetry |
| `KartingSimulation.jsx` | Standalone zone-based trajectory alert simulation (no hardware required) |

---

## 3. Known Open Items (not yet finalized, flag if the coding agent asks)

- Real hardware integration (ESP32 firmware for glove and kart unit) is not
  part of this build — the backend should accept telemetry over a REST/
  WebSocket endpoint shaped like the real device output, so hardware can be
  connected later without an API redesign.
- Track survey and automatic zone-boundary detection (heading-change
  calculation, coach confirms/names zones) is part of Phase 1 scope but not
  yet detailed as an API spec — build the `tracks`/`zones` data model to
  support it, but the survey-lap UI flow itself may need further scoping
  during the build.
- Camera-clip capture (Phase 1.5) is confirmed as a rolling-buffer approach
  but no camera hardware has been selected yet.
