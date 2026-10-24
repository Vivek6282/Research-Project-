# Trackside — Input validation, field by field

All checks run on the server (DRF serializers and views); frontend checks are only for convenience. Unknown
fields in a JSON body are ignored and never written; read-only fields cannot be set. The database is reached
only through the Django ORM (no raw SQL), React escapes all text (no `dangerouslySetInnerHTML`), and no input
reaches a shell. JSON bodies are capped at 2.5 MB by Django (`DATA_UPLOAD_MAX_MEMORY_SIZE`).

## Sign-in and users

| Endpoint | Field | Type | Required | Rule | Error message |
|---|---|---|---|---|---|
| `POST auth/login/` | identifier (or email) | text | yes | 1–254 characters | `Email or Driver ID is required.` / length message |
| | password | text | yes | ≤ 256 characters | length message; wrong → `Invalid email/username or password.` |
| `POST auth/users/` | name | text | yes | 1–150 characters | DRF required/length message |
| | role | enum | yes | `coach` or `driver` (`admin` refused) | `Admin accounts cannot be created through the API…` |
| | email | email | coach: yes, driver: no | valid address, unique | `Email address is required for Coach accounts.` / already used |
| | password | text | yes | 8+ characters, not common, not all digits, not like name/email/username/driver ID | Django's message per broken rule, under `password` |
| `PATCH auth/users/<id>/` | same as above, all optional | | | cannot deactivate or demote yourself or the last admin; `driver_code` only for drivers, `D` + 5 digits, unique | field messages |
| `DELETE auth/users/<id>/` | confirm | text | yes | exactly the driver ID (drivers) or username | `Type … exactly to confirm. Nothing was deleted.` |

## Sessions and readings

| Endpoint | Field | Type | Required | Rule | Error message |
|---|---|---|---|---|---|
| `POST sessions/` | driver | user id | coach/admin: yes | an **active driver** (drivers: forced to themselves) | `Choose an active driver.` |
| | track | track id | yes | existing track | DRF message |
| | mode | enum | no | `safety` / `performance` | DRF choice message |
| | goal_text | text | no | ≤ 500 characters | length message |
| | goal_passed | yes/no/null | no | ignored when a driver creates the session | — |
| | kart_number | text | no | ≤ 20 characters | length message |
| | started_at | date-time | yes | ISO 8601 | DRF format message |
| `POST sessions/<id>/telemetry/` | body | object or list | yes | list of at most 100 readings | `Batch size cannot exceed 100 readings.` |
| | lateral_g | number | yes | finite, 0–10 | `lateral_g must be a finite number between 0.0 and 10.0.` |
| | speed_kmh | number | yes | finite, 0–300 | range message |
| | gps_lat / gps_lng | number | no | finite, −90…90 / −180…180 | range message |
| | lap_number | integer | no | 1–999 | range message |
| | recorded_at | date-time | yes | not more than 5 min in the future | `recorded_at cannot be more than 5 minutes in the future.` |
| | (session) | | | not ended | 409 `Cannot post telemetry to an ended session.` |
| `POST sessions/<id>/biometrics/` | heart_rate | integer | yes | 20–250 | DRF range message |
| | spo2 | integer | yes | 50–100 | DRF range message |
| | breathing_rate | integer | no | 3–80 | DRF range message |
| | recorded_at | date-time | yes | not more than 5 min in the future | as above |
| `POST sessions/<id>/notes/` | note_text | text | yes | 1–2000 characters | required/length message |
| | zone | zone id | no | must be a corner of the **session's track** | `This corner is not on the session's track.` |

## Maps and corners

| Endpoint | Field | Rule | Error message |
|---|---|---|---|
| `POST tracks/import/preview/` | file | `.csv` (RaceChrono) or `.vbo` only, ≤ 5 MB, ≤ 200,000 rows, ≥ 50 valid GPS samples; read in memory, never stored or executed | clear 4xx message per problem |
| `POST tracks/import/confirm/`, `draw/confirm/` | name | 1–150 characters, unique among active maps | name message |
| | corners | ≤ 50,000 characters of JSON; label 1–40, limit within the kart class range (0.3–1.5 g sprint) | per-corner message |
| `POST tracks/draw/preview/` | points | 8–1000 clicks, loop 100 m–20 km, within 15 km of its centre | `Click 8 to 1000 points around the track.` etc. |
| Zones (add/edit) | label | 1–40 characters, no control characters, not starting with "Straight" | `A corner name …` |
| | gps_range | object with `start`, `end` (`lat` −90…90, `lng` −180…180), optional `center`, `length_m`; nothing else | `gps_range …` |
| | threshold_g | inside the track's allowed range | `The limit must be from … to … g.` |

## Devices and preferences

| Endpoint | Field | Rule | Error message |
|---|---|---|---|
| `POST devices/` | device_type | `glove` / `kart_unit` / `biometric_strap` | choice message |
| | assigned_to | an active driver, one device per type per driver | assignment message |
| `POST devices/me/commands/<id>/complete/` | status | `completed` or `failed` | `Use 'completed' or 'failed'.` |
| | result | an object of at most 4096 bytes, or nothing; only while the command is pending | 400 size message / 409 `This command is already finished.` |
| `PATCH preferences/me/` | font_size | one of the allowed sizes | choice message |
| | tutorial_completed | true/false | DRF message |

URL parameters are typed by the router (`<uuid:…>`), so a malformed id never reaches a view (404). The only
query parameter that changes data selection, `tracks/?archived=`, accepts `only` or `all`; anything else
falls back to the normal list.
