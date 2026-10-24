# Trackside — Security test checklist

Each row is an attack or mistake, the expected answer, and the automated test that proves it. Run the
backend suite with `python manage.py test` in `backend/`; the Selenium suite with `pytest e2e/`.

## Examples per role

| Who | Valid request | Answer | Invalid request | Answer |
|---|---|---|---|---|
| Signed out | `POST /api/auth/login/` with a real account | 200 | `GET /api/sessions/` | 401/403 |
| Driver | `GET /api/sessions/` | 200, only own sessions | `GET /api/auth/users/` | 403 |
| Driver | `POST /api/sessions/` with `goal_passed: true` | 201, goal result left empty | `POST /api/sessions/<someone else's>/telemetry/` | 403, nothing saved |
| Coach | `POST /api/sessions/<id>/notes/` with `note_text` | 201 | the same with a corner of another track | 400 |
| Coach | `POST /api/sessions/` for a driver | 201 | the same with a coach as `driver` | 400 `Choose an active driver.` |
| Admin | `POST /api/auth/users/` with a strong password | 201 | the same with `password123` | 400, reasons under `password` |
| Device | report a pending self-test result | 200 | report it again, or send 5 KB | 409 / 400 |

## Bypass attempts

| Attempt | Expected | Test |
|---|---|---|
| Any private route while signed out | refused | `accounts/tests/test_access_sweep.py` (every route, every method, from the URL table) |
| Driver on admin/staff routes (vertical) | refused | `test_access_sweep.py::test_a_driver_is_refused_on_admin_and_staff_routes` |
| Coach on admin-only routes (vertical) | refused | `test_access_sweep.py::test_a_coach_is_refused_on_admin_only_routes` |
| Driver B reads or writes driver A's data (horizontal) | refused, nothing saved | `test_access_sweep.py::TestWritesToSomeoneElsesSession`, `test_another_driver_cannot_reach_…` |
| Driver promotes themself / changes role via `me` | refused | `test_access_sweep.py::test_a_driver_cannot_promote_themselves` |
| POST without CSRF token | refused | `test_access_sweep.py::test_a_signed_in_post_without_the_csrf_token_is_refused` |
| Driver page cookie used as coach (two roles, one browser) | refused | `accounts/tests/test_area_sessions.py` |
| Guess which accounts exist from the answer or its timing | same answer, same hashing | `accounts/tests/test_audit_fixes_accounts.py` |
| Password guessing | 5/min per address, 10/min per account, lockout after 10 wrong | `test_rate_limiting.py`, `test_sign_in_hardening.py::TestLockout` |
| Spread guesses over email, username and driver ID | one shared counter | `test_sign_in_hardening.py::test_email_username_and_driver_id_share_one_counter` |
| Find accounts through the lockout | same answer for unknown accounts | `test_sign_in_hardening.py::test_unknown_account_locks_the_same_way` |
| Huge password to burn server time | 400 before hashing | `test_sign_in_hardening.py::test_oversized_login_fields_are_refused` |
| Passwords in logs | never written | `test_sign_in_hardening.py::test_security_log_has_events_but_never_the_password` |
| Weak password set by the admin | 400 with reasons | `test_sign_in_hardening.py::TestPasswordRules` |
| Session for a coach/admin, self-passed goal | 400 / ignored | `driving_sessions/tests/test_input_hardening.py::TestSessionInput` |
| Oversized note or goal, note on another track's corner | 400 | `test_input_hardening.py::TestNoteInput`, `TestSessionInput` |
| Impossible biometric values or future times | 400 | `test_input_hardening.py::TestBiometricInput` |
| Impossible telemetry, batches over 100, ended session | 400 / 409 | `driving_sessions/tests/test_telemetry_security.py` |
| Device reads or completes another device's command | refused | `devices/tests/test_commands.py`, `test_device_command_access.py` |
| Device overwrites a result or sends a huge one | 409 / 400 | `devices/tests/test_commands.py::DeviceCommandResultLimitsTestCase` |
| Forged or wrong device token | 401/403 | `devices/tests/test_device_authentication.py` |
| Bad or oversized map files | 4xx, nothing stored | `tracks/tests/test_track_import_upload.py` |
| Built-in Demo Circuit changed | 409 | `tracks/tests/test_track_archive.py`, `test_corner_editor.py` |
| Private answers cached by a browser or proxy | `Cache-Control: no-store` | `accounts/tests/test_private_headers.py` |
| Admin deletes without typing the confirmation | 400, nothing deleted | `accounts/tests/test_deactivation.py::test_delete_user_needs_the_typed_confirmation`; Selenium `TC-ADMIN-07` |

## By hand after a deploy

1. Sign in with a wrong password 10 times, then the right one: the page says to wait 15 minutes.
2. As a driver, open `/api/auth/users/` in the browser: refused.
3. As the admin, create a user with `password123`: the form shows why it is refused.
4. Check the server log for `auth.login_failed` lines: account ids only, no passwords.
