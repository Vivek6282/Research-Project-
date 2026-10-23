# Trackside backend

## Removing users

There are two ways to take a person out of the system. **Deactivate is the recommended default.**

| | Deactivate | Permanent delete |
|---|---|---|
| Who can log in afterwards | nobody (the account is blocked) | the account no longer exists |
| Their data | kept | removed (see below) |
| Undo | Reactivate in the Admin screen | not possible (restore a backup) |

### What a permanent delete removes

* **A driver:** all their sessions, with every reading, alert, biometric reading and coach note on those sessions, plus their own corner limits and preferences. Devices assigned to them become **unassigned** and stay.
* **A coach:** every session note they wrote, **on anyone's session**, plus their preferences.
* **Kept:** audit-log entries (their actor is cleared), tracks and maps.

### Safeguards (Admin screen and API)

* Admin only. `GET /api/auth/users/<id>/delete-preview/` shows exactly what would be removed and changes nothing.
* `DELETE /api/auth/users/<id>/` needs the body `{"confirm": "<driver ID, or the username for a coach>"}`, typed exactly (case-sensitive). Wrong text: 400, nothing deleted.
* Refused with 409: your own account, any Admin account, and a driver who is **live right now** (an open session with a recent reading).
* Every delete writes a `DELETE_USER` audit entry (role, driver ID and the counts) in the same transaction as the delete.

### Driver IDs

Every driver has a short display ID, the letter `D` and 5 digits (for example `D17256`). It is for display only: logins stay as email or `TRK-...`. New drivers get a random unused ID automatically; an Admin can change it (unique, drivers only).

### Command-line tools

**Run these only after a backup of the database** (copy `db.sqlite3`, or `pg_dump` for PostgreSQL). They change data for good.

* `python manage.py prune_users` removes unneeded Coach/Driver accounts. It is a **dry run** unless you add `--apply` (then you type `DELETE`). It never touches Admins and, by default, only removes users with nothing attached; `--include-with-data` also removes their sessions. Protect people with `--keep EMAIL_OR_USERNAME`, `--keep-name "Full Name"` (case and surrounding spaces ignored) and `--keep-code D17256`. Each `--keep-name` / `--keep-code` must match exactly one user or the command stops and deletes nothing. The report starts with **KEEPING**, then **DELETING** with each user's data.

  ```
  python manage.py prune_users --role driver --include-with-data --keep-name "Marco Ferrati" --keep-name "Anaya Iyer"
  ```

* `python manage.py set_driver_identity (--email X | --username X | --name "Current Name") [--new-name "Marco Ferrati"] [--code D17256]` sets the name and/or driver ID of exactly one driver, prints before and after, and writes an audit entry. It touches nothing else.

## Sign-ins: one per role

Each role keeps its own session cookie: `sessionid_admin`, `sessionid_coach`, `sessionid_driver`. A page tells the server which one it uses with the `X-Trackside-Area` header (live feeds: `?area=`), so a driver tab and a coach tab stay signed in together in one browser and never turn into each other. The login request sends `auto`, and the server puts the sign-in into the cookie of the signed-in account's own role. Rights are never taken from the area: they come from the account's role on every request, and a request that names an area gets only that area's cookie. With no header the old single `sessionid` cookie is used exactly as before (tests and scripts). The code is `config/area_session.py`, tested in `accounts/tests/test_area_sessions.py`.

## Draw a track on the map

`POST /api/tracks/draw/preview/` and `POST /api/tracks/draw/confirm/` (Admin and Coach, 60 a hour each) take the points clicked on a map (`points: [{lat, lng}]`, 8 to 1,000, loop 100 m to 20 km). The server joins them into a smooth closed curve (a centripetal Catmull-Rom spline), spaces it evenly (about 2 m) and smooths it like an imported lap, then uses the same corner finder, name checks and saver as a file import, so the map is stored with `source = "drawn"`. Preview answers in the same shape as an import preview; confirm rebuilds the outline from the points and never trusts an outline sent by the browser. The code is `tracks/importing/drawn.py` and `tracks/views_draw.py`.

`MAP_TILE_HOSTS` (default `https://tile.openstreetmap.org`) lists the hosts the page may load map pictures from; it goes into the page's content policy (`img-src`) and each entry must be a plain `https://host` (a path, space, semicolon or `http` stops the server from starting). The site also sends `Referrer-Policy: strict-origin-when-cross-origin`, so tile servers see the site's address but never which page is open.

## Where limits come from

* A corner's g-force limit is `zone.threshold_g`, set on the map (Maps, then **Edit corners**, 0.3 to 1.5 g). It applies to everyone who drives that map. Alerts (`Alert.threshold_applied`), live events, roster status, the simulator profile and the Play demo status all read it through `drivers/limits.py` (`limit_in_force`).
* The built-in Demo Circuit is locked; duplicate it as a custom map to change its limits.
* **Per-driver limits are retired.** Old `DriverZoneThreshold` rows are kept as history, unused (no data was deleted or migrated). `POST /api/drivers/thresholds/` answers `410 Gone`; the list endpoints stay read-only. The Admin delete screen still counts those rows, and they are removed with the driver.

## Production variables

Set these in the backend's environment (`.env`). With `DJANGO_ENV=production` the backend refuses to start on a weak `SECRET_KEY`, on SQLite, or on an origin that does not start with `https://`.

| Variable | Example | What it does |
|---|---|---|
| `DJANGO_ENV` | `production` | Turns on the production rules: secure cookies, HTTPS redirect, HSTS, trusted proxy header, no SQLite. |
| `DEBUG` | `False` | Must be `False` in production. |
| `SECRET_KEY` | output of `python -c "import secrets; print(secrets.token_urlsafe(50))"` | Signs sessions. Long, random, never shared; a placeholder or empty value is refused. |
| `ALLOWED_HOSTS` | `trackside.example.com,localhost,127.0.0.1` | Host names the backend answers to (also used by the WebSocket origin check). Keep `localhost` so the container health check works. |
| `DATABASE_URL` | `postgres://trackside_user:PASSWORD@db:5432/trackside` | PostgreSQL connection. SQLite is refused in production. |
| `REDIS_URL` | `redis://:PASSWORD@redis:6379/0` | Redis for live WebSocket updates. Empty means an in-memory layer (one process only). |
| `CORS_ALLOWED_ORIGINS` | `https://trackside.example.com` | The site(s) allowed to call the API with cookies (comma separated, each `https://`). The older name `CORS_ALLOWED_ORIGIN` is still accepted. |
| `CSRF_TRUSTED_ORIGINS` | `https://trackside.example.com` | Optional extra origins trusted for form/API posts (comma separated, each `https://`). The CORS origins are always trusted too. |
| `TRUSTED_PROXY_COUNT` | `1` | How many reverse proxies sit in front (default 1 in production, 0 otherwise). The proxy must append the real client address to `X-Forwarded-For` and must replace, not trust, any value the client sent; otherwise login limits can be dodged or shared by everyone. |

Behind the proxy the backend trusts `X-Forwarded-Proto` (so HTTPS requests are not redirected again). `GET /api/health/` answers `200 {"status": "ok"}` when the database answers, otherwise `503`, and reveals nothing else; it is exempt from the HTTPS redirect so the container health check can call it.
