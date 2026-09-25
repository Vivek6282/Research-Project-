"""Authentication and Role-Based Access Control E2E Test Suite for Trackside."""

import pytest
import requests
from e2e.pages.login_page import LoginPage
from e2e.pages.admin_page import AdminDashboardPage
from e2e.pages.coach_page import CoachDashboardPage
from e2e.pages.driver_page import DriverDashboardPage
from e2e.pages.shared_ui import TopBar
from e2e.conftest import ADMIN_CREDENTIALS, COACH_CREDENTIALS, DRIVER1_CREDENTIALS, DRIVER2_CREDENTIALS


def test_tc_auth_01_valid_login_redirects_by_role(driver, base_url):
    """TC-AUTH-01: Valid login for each role redirects to the correct dashboard (/admin, /coach, /driver)."""
    login_page = LoginPage(driver, base_url)
    top_bar = TopBar(driver, base_url)

    # 1. Admin Login
    login_page.open()
    login_page.login(
        role="admin",
        identifier=ADMIN_CREDENTIALS["identifier"],
        password=ADMIN_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/admin")
    assert "/admin" in driver.current_url

    # 2. Coach Login
    top_bar.sign_out()
    login_page.wait_for_url_contains("/login")
    login_page.login(
        role="coach",
        identifier=COACH_CREDENTIALS["identifier"],
        password=COACH_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/coach")
    assert "/coach" in driver.current_url

    # 3. Driver Login
    top_bar.sign_out()
    login_page.wait_for_url_contains("/login")
    login_page.login(
        role="driver",
        identifier=DRIVER1_CREDENTIALS["identifier"],
        password=DRIVER1_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/driver")
    assert "/driver" in driver.current_url


def test_tc_auth_02_login_with_email_and_username(driver, base_url):
    """TC-AUTH-02: Login with email and login with auto-generated username (TRK-DRV-xxxxxx) both succeed."""
    login_page = LoginPage(driver, base_url)
    top_bar = TopBar(driver, base_url)

    # 1. Login with email
    login_page.open()
    login_page.login(
        role="driver",
        identifier=DRIVER1_CREDENTIALS["identifier"],
        password=DRIVER1_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/driver")
    assert "/driver" in driver.current_url

    # 2. Login with auto-generated username ID
    top_bar.sign_out()
    login_page.wait_for_url_contains("/login")
    login_page.login(
        role="driver",
        identifier=DRIVER1_CREDENTIALS["username"],
        password=DRIVER1_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/driver")
    assert "/driver" in driver.current_url


def test_tc_auth_03_wrong_password_shows_error(driver, base_url):
    """TC-AUTH-03: Wrong password shows an error and stays on /login."""
    login_page = LoginPage(driver, base_url)
    login_page.open()
    login_page.login(
        role="coach",
        identifier=COACH_CREDENTIALS["identifier"],
        password="WrongPassword999!",
    )
    assert login_page.is_error_displayed()
    error_msg = login_page.get_error_message()
    assert len(error_msg) > 0
    assert "/login" in driver.current_url


def test_tc_auth_04_deactivated_user_cannot_login(driver, base_url, backend_url):
    """TC-AUTH-04: Deactivated user cannot log in."""
    session = requests.Session()
    csrf_resp = session.get(f"{backend_url}/api/auth/csrf/", timeout=5)
    csrf_token = csrf_resp.cookies.get("csrftoken", "")

    # Log in as admin to deactivate Driver 2
    session.post(
        f"{backend_url}/api/auth/login/",
        json={"identifier": ADMIN_CREDENTIALS["identifier"], "password": ADMIN_CREDENTIALS["password"]},
        headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
        timeout=5,
    )
    csrf_token = session.cookies.get("csrftoken", csrf_token)

    users_res = session.get(f"{backend_url}/api/auth/users/", timeout=5).json()
    user_list = users_res if isinstance(users_res, list) else users_res.get("results", [])
    target_user = next((u for u in user_list if u.get("email") == DRIVER2_CREDENTIALS["identifier"]), None)

    assert target_user is not None, "Driver 2 account not found"
    target_id = target_user["id"]

    try:
        # Deactivate user
        session.patch(
            f"{backend_url}/api/auth/users/{target_id}/",
            json={"is_active": False},
            headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
            timeout=5,
        )

        # Attempt to login in browser as deactivated driver
        login_page = LoginPage(driver, base_url)
        login_page.open()
        login_page.login(
            role="driver",
            identifier=DRIVER2_CREDENTIALS["identifier"],
            password=DRIVER2_CREDENTIALS["password"],
        )

        assert login_page.is_error_displayed()
        assert "/login" in driver.current_url
    finally:
        # Reactivate user for future tests
        csrf_token = session.cookies.get("csrftoken", csrf_token)
        session.patch(
            f"{backend_url}/api/auth/users/{target_id}/",
            json={"is_active": True},
            headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
            timeout=5,
        )


def test_tc_auth_05_unauthenticated_redirected_to_login(driver, base_url):
    """TC-AUTH-05: Unauthenticated user visiting /admin, /coach, /driver directly is redirected to /login."""
    login_page = LoginPage(driver, base_url)

    # Clear all cookies/sessions
    driver.get(f"{base_url}/login")
    driver.delete_all_cookies()

    for path in ["/admin", "/coach", "/driver"]:
        driver.get(f"{base_url}{path}")
        login_page.wait_for_url_contains("/login")
        assert "/login" in driver.current_url


def test_tc_auth_06_role_guard_blocks_unauthorized_dashboard(driver, base_url):
    """TC-AUTH-06: A Driver visiting /admin or /coach directly is blocked (role guard works, not just hidden links)."""
    login_page = LoginPage(driver, base_url)

    # Login as Driver
    login_page.open()
    login_page.login(
        role="driver",
        identifier=DRIVER1_CREDENTIALS["identifier"],
        password=DRIVER1_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/driver")

    # Attempt direct navigation to /admin
    driver.get(f"{base_url}/admin")
    # Must be redirected back or blocked (cannot remain on /admin)
    login_page.wait_for_url_matches(r".*(/driver|/login).*")
    assert "/admin" not in driver.current_url

    # Attempt direct navigation to /coach
    driver.get(f"{base_url}/coach")
    login_page.wait_for_url_matches(r".*(/driver|/login).*")
    assert "/coach" not in driver.current_url


def test_tc_auth_07_sign_out_and_back_navigation(driver, base_url):
    """TC-AUTH-07: Sign out returns to /login and back-navigation doesn't restore the session."""
    login_page = LoginPage(driver, base_url)
    top_bar = TopBar(driver, base_url)

    # Log in as Coach
    login_page.open()
    login_page.login(
        role="coach",
        identifier=COACH_CREDENTIALS["identifier"],
        password=COACH_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/coach")

    # Sign out
    top_bar.sign_out()
    login_page.wait_for_url_contains("/login")
    assert "/login" in driver.current_url

    # Attempt browser back navigation
    driver.back()
    # Ensure back navigation does not reveal active protected dashboard
    assert not CoachDashboardPage(driver, base_url).is_visible("coach-panel-live-trajectory", timeout=2)

    # Attempt direct navigation to protected route
    driver.get(f"{base_url}/coach")
    login_page.wait_for_url_contains("/login")
    assert "/login" in driver.current_url
