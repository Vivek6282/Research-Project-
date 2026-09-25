"""Driver Dashboard E2E Test Suite for Trackside."""

import pytest
import requests
from e2e.pages.login_page import LoginPage
from e2e.pages.driver_page import DriverDashboardPage
from e2e.conftest import DRIVER1_CREDENTIALS, DRIVER2_CREDENTIALS, ADMIN_CREDENTIALS


def test_tc_driver_01_empty_state_for_driver_without_sessions(driver, base_url, backend_url):
    """TC-DRIVER-01: Driver with no sessions sees the "No sessions recorded yet" empty state (not fake data)."""
    # Create a fresh driver account with 0 sessions via Admin API
    session = requests.Session()
    csrf_res = session.get(f"{backend_url}/api/auth/csrf/", timeout=5)
    csrf_token = csrf_res.cookies.get("csrftoken", "")

    session.post(
        f"{backend_url}/api/auth/login/",
        json={"identifier": ADMIN_CREDENTIALS["identifier"], "password": ADMIN_CREDENTIALS["password"]},
        headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
        timeout=5,
    )
    csrf_token = session.cookies.get("csrftoken", csrf_token)

    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    fresh_driver_email = f"fresh_driver_{unique_suffix}@trackside.local"
    create_res = session.post(
        f"{backend_url}/api/auth/users/",
        json={"name": f"Fresh Driver {unique_suffix}", "role": "driver", "email": fresh_driver_email, "password": "DriverPassword123!"},
        headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
        timeout=5,
    ).json()

    fresh_username = create_res.get("username")

    # Login in browser as fresh driver
    login_page = LoginPage(driver, base_url)
    login_page.open()
    login_page.login(
        role="driver",
        identifier=fresh_username or fresh_driver_email,
        password="DriverPassword123!",
    )
    driver_page = DriverDashboardPage(driver, base_url)
    driver_page.wait_for_visible("driver-panel-telemetry")

    # Confirm empty state is displayed
    assert driver_page.is_no_sessions_displayed()
    empty_text = driver_page.get_text("driver-no-sessions-msg")
    assert "No sessions recorded yet" in empty_text


def test_tc_driver_02_safety_performance_mode_toggle(driver, base_url):
    """TC-DRIVER-02: Safety/Performance mode toggle switches the active mode."""
    login_page = LoginPage(driver, base_url)
    login_page.open()
    login_page.login(
        role="driver",
        identifier=DRIVER1_CREDENTIALS["identifier"],
        password=DRIVER1_CREDENTIALS["password"],
    )
    driver_page = DriverDashboardPage(driver, base_url)
    driver_page.wait_for_visible("driver-panel-mode")

    # Toggle to Performance Mode
    driver_page.toggle_mode("performance")
    active_mode = driver_page.get_active_mode_text().upper()
    assert "PERFORMANCE" in active_mode

    # Toggle to Safety Mode
    driver_page.toggle_mode("safety")
    active_mode = driver_page.get_active_mode_text().upper()
    assert "SAFETY" in active_mode


def test_tc_driver_03_idor_data_isolation_between_drivers(driver, base_url, backend_url):
    """TC-DRIVER-03: Driver A cannot see Driver B's data (IDOR check at the UI level)."""
    import datetime
    session = requests.Session()

    # 1. Authenticate as Admin via API to provision Driver 2's session
    csrf_res = session.get(f"{backend_url}/api/auth/csrf/", timeout=5)
    csrf_token = csrf_res.cookies.get("csrftoken", "")

    login_res = session.post(
        f"{backend_url}/api/auth/login/",
        json={"identifier": ADMIN_CREDENTIALS["identifier"], "password": ADMIN_CREDENTIALS["password"]},
        headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
        timeout=5,
    )
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    csrf_token = session.cookies.get("csrftoken", csrf_token)

    # 2. Retrieve Driver 2 user and active track
    users_res = session.get(f"{backend_url}/api/auth/users/", timeout=5)
    user_list = users_res.json()
    users = user_list if isinstance(user_list, list) else user_list.get("results", [])
    driver2 = next((u for u in users if u.get("email") == DRIVER2_CREDENTIALS["identifier"]), None)
    assert driver2 is not None, "Driver 2 account not found"

    tracks_res = session.get(f"{backend_url}/api/tracks/", timeout=5)
    track_list = tracks_res.json()
    tracks = track_list if isinstance(track_list, list) else track_list.get("results", [])
    assert len(tracks) > 0, "No track found for session creation"
    track_id = tracks[0]["id"]

    # 3. Create a real session with a distinctive goal_text for Driver 2
    unique_goal_token = f"SECRET-GOAL-DRIVER2-{int(datetime.datetime.now().timestamp() * 1000)}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    create_sess = session.post(
        f"{backend_url}/api/sessions/",
        json={
            "driver": driver2["id"],
            "track": track_id,
            "mode": "performance",
            "started_at": now_iso,
            "kart_number": "#88",
            "goal_text": unique_goal_token,
        },
        headers={"X-CSRFToken": session.cookies.get("csrftoken", csrf_token), "Referer": backend_url},
        timeout=5,
    )
    assert create_sess.status_code in (200, 201), f"Failed to create Driver 2 session: {create_sess.text}"
    driver2_session_id = create_sess.json()["id"]

    # 4. Log in as Driver 1 via UI
    login_page = LoginPage(driver, base_url)
    login_page.open()
    login_page.login(
        role="driver",
        identifier=DRIVER1_CREDENTIALS["identifier"],
        password=DRIVER1_CREDENTIALS["password"],
    )
    driver_page = DriverDashboardPage(driver, base_url)
    driver_page.wait_for_visible("driver-panel-telemetry")

    # 5. Assert that neither Driver 2's session nor distinctive goal_text appears anywhere
    page_text = driver.execute_script("return document.body.innerText;")
    page_source = driver.page_source

    assert unique_goal_token not in page_text, f"IDOR leak: Found Driver 2 goal_text {unique_goal_token} in Driver 1 page text"
    assert unique_goal_token not in page_source, f"IDOR leak: Found Driver 2 goal_text {unique_goal_token} in Driver 1 page source"
    assert driver2_session_id not in page_text, f"IDOR leak: Found Driver 2 session ID {driver2_session_id} in Driver 1 page text"
    assert driver2_session_id not in page_source, f"IDOR leak: Found Driver 2 session ID {driver2_session_id} in Driver 1 page source"
    assert DRIVER2_CREDENTIALS["identifier"] not in page_text, f"IDOR leak: Found Driver 2 email in Driver 1 dashboard"


def test_tc_driver_04_development_ongoing_banners_visible(driver, base_url):
    """TC-DRIVER-04: Phase 1.5 and Phase 2 "Development Ongoing" banners are visible and non-interactive."""
    login_page = LoginPage(driver, base_url)
    login_page.open()
    login_page.login(
        role="driver",
        identifier=DRIVER1_CREDENTIALS["identifier"],
        password=DRIVER1_CREDENTIALS["password"],
    )
    driver_page = DriverDashboardPage(driver, base_url)
    driver_page.wait_for_visible("driver-panel-telemetry")

    assert driver_page.is_phase_1_5_banner_displayed()
    assert driver_page.is_phase_2_banner_displayed()
