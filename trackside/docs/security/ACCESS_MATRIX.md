# Trackside — Authentication and access matrix

Stack: Django 5.2 + DRF + Channels backend, React frontend. Roles: **Admin**, **Coach**, **Driver**, plus
**Device** (an ESP32 or the laptop link signing in with its own token). Every rule below is enforced on the
server; the frontend only hides buttons.

## 1. Authentication

| Topic | How Trackside does it | Where |
|---|---|---|
| Accounts | No self-registration. Only the Admin creates Coach and Driver accounts; Admin accounts only via `manage.py seed_admin`. | `accounts/serializers.py` (`validate_role`) |
| Passwords | Hashed with Django's PBKDF2-SHA256 (never stored or logged in plain text). New and changed passwords must pass length (8+), common-password, all-numeric and similar-to-name/email/username/driver-ID checks. | `accounts/password_rules.py`, `AUTH_PASSWORD_VALIDATORS` |
| Sign-in | `POST /api/auth/login/` with email, username or driver ID. The same answer and the same hashing time whether or not the account exists: `Invalid email/username or password.` | `accounts/views_auth.py` |
| Brute force | Per address: 5/min (`LOGIN_THROTTLE_RATE`). Per typed identifier: 10/min (`LOGIN_ACCOUNT_THROTTLE_RATE`). **Lockout**: 10 wrong passwords in 15 min lock that account (email, username and driver ID share one counter) for 15 min, even with the right password; unknown identifiers lock the same way. | `accounts/throttles.py`, `accounts/login_guard.py` |
| Sessions | HttpOnly session cookie per role area (`sessionid_admin/coach/driver`), new key at every sign-in (no fixation), `Secure` + HSTS in production, `SameSite=Lax`, ends after 12 h (`SESSION_COOKIE_AGE`). Nothing secret in URLs: no tokens, passwords or session ids in links. | `config/settings.py`, `config/area_session.py` |
| CSRF | Every POST/PUT/PATCH/DELETE from the browser needs the `X-CSRFToken` header (double-submit cookie). | DRF `SessionAuthentication` |
| Sign-out | `POST /api/auth/logout/` deletes the server-side session. | `accounts/views_auth.py` |
| Password reset | The Admin sets a new password in the user editor (same strength rules). There is no e-mail reset link: the site sends no e-mail, and most drivers have no e-mail address. | `accounts/serializers.py` |
| Devices | Each device has its own random token; only its SHA-256 hash is stored; compared in constant time. | `devices/authentication.py` |
| Live feed (WebSocket) | Uses the same role-area session cookie; refused without a valid sign-in and access to that session. | `driving_sessions/consumers.py` |
| Logging | `trackside.security` logger: `auth.login_ok`, `auth.login_failed`, `auth.login_locked`, `auth.logout` with account id and address. Never the password, the typed text of an unknown identifier, or a session key. Lockouts of real accounts also appear in the Admin audit log (`SIGN_IN_LOCKED`). | `accounts/login_guard.py`, `config/logging_config.py` |
| General rate cap | Every endpoint without its own limit: 1200 requests/min per user (`USER_THROTTLE_RATE`). | `config/settings.py` |

## 2. Who may do what

✓ = allowed. **own** = only their own records. — = refused (401 signed out, 403 wrong role, 404 where existence would leak).

| Module / endpoint | Action | Admin | Coach | Driver | Device |
|---|---|---|---|---|---|
| Sign-in, CSRF, health | use | ✓ (public) | ✓ | ✓ | ✓ |
| Own profile `auth/me` | read | ✓ | ✓ | ✓ | — |
| Users `auth/users` | list, create, read, edit, deactivate, delete (typed confirmation) | ✓ | — | — | — |
| Audit log, diagnostics | read | ✓ | — | — | — |
| Tracks `tracks/` | list, read, reference line | ✓ | ✓ | ✓ | — |
| | create | ✓ | — | — | — |
| | edit | ✓ | — | — | — |
| | archive/delete, restore, duplicate | ✓ | ✓ | — | — |
| Map import / draw / demo circuit / survey | create | ✓ | ✓ | — | — |
| Corners (zones) | read | ✓ | ✓ | ✓ | — |
| | add, corner editor save | ✓ | ✓ | — | — |
| | edit/retire one zone | ✓ | — | — | — |
| | limit history | ✓ | ✓ | — | — |
| Sessions `sessions/` | list, read | ✓ | ✓ | own | assigned driver's |
| | create | ✓ (any driver) | ✓ (any driver) | own (cannot set goal result) | — |
| | edit, delete | ✓ | ✓ | — | — |
| | finish | ✓ | ✓ | — | assigned driver's |
| Telemetry | read | ✓ | ✓ | own | assigned driver's |
| | write | ✓ | ✓ | own | assigned driver's |
| Alerts, alert summary, corner times, roster | read | ✓ | ✓ | own | — |
| Biometrics | read, write | ✓ | ✓ | own | assigned driver's (write) |
| Coach notes | read | ✓ | ✓ | own sessions | — |
| | write | — | ✓ | — | — |
| Old per-driver limits `drivers/` | read (history) | ✓ | ✓ | own | — |
| | write | retired (410 Gone) | retired (410 Gone) | — | — |
| Devices `devices/` | list, read | ✓ | ✓ (no key hash) | — | — |
| | create, edit, assign, delete, send command | ✓ | — | — | — |
| Device commands `devices/me/commands` | read pending, report result (once, ≤ 4 KB) | — | — | — | own |
| Preferences `preferences/me` | read, edit | own | own | own | — |
| Demo simulator `demo/` | start, stop, status (off in production) | — | ✓ | — | — |
| Laptop link `laptop-link/` | start, stop, status | ✓ | ✓ | — | — |

Ownership is decided on the server from the signed-in account (`driving_sessions/access.py`: `sessions_visible_to`,
`can_access_session`). Client-sent role values, user ids and hidden fields are never trusted: the session's
`driver` is forced to the signed-in driver, notes take their coach from the sign-in, and read-only fields
(`is_demo`, `username`, `api_key_hash`, …) cannot be written.

## 3. Status codes

| Situation | Code |
|---|---|
| Not signed in | 401 (or 403 from CSRF/session checks) |
| Signed in, wrong role | 403 |
| A user, device, track or session that does not exist, or a device/driver record you may not know about | 404 (same body as missing) |
| Invalid input | 400 with a message per field |
| Conflicts (ended session, finished command, built-in map) | 409 |
| Too many requests or locked sign-in | 429 |

Known, accepted difference: a driver reaching another driver's **session-scoped** route (telemetry, biometrics,
notes) gets 403 rather than 404. Session ids are random UUIDs, so this reveals nothing guessable; it is kept
because the existing apps and tests rely on it.
