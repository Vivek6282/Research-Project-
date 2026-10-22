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

## Where limits come from

* A corner's g-force limit is `zone.threshold_g`, set on the map (Maps, then **Edit corners**, 1.0 to 1.5 g). It applies to everyone who drives that map. Alerts (`Alert.threshold_applied`), live events, roster status, the simulator profile and the Play demo status all read it through `drivers/limits.py` (`limit_in_force`).
* The built-in Demo Circuit is locked; duplicate it as a custom map to change its limits.
* **Per-driver limits are retired.** Old `DriverZoneThreshold` rows are kept as history, unused (no data was deleted or migrated). `POST /api/drivers/thresholds/` answers `410 Gone`; the list endpoints stay read-only. The Admin delete screen still counts those rows, and they are removed with the driver.
