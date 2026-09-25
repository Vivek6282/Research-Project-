"""Responsive Layout E2E Test Suite for Trackside across 375px, 768px, and 1440px."""

import pytest
from e2e.pages.login_page import LoginPage
from e2e.pages.admin_page import AdminDashboardPage
from e2e.pages.coach_page import CoachDashboardPage
from e2e.conftest import ADMIN_CREDENTIALS, COACH_CREDENTIALS, DRIVER1_CREDENTIALS


def test_tc_resp_01_no_horizontal_overflow_at_any_viewport(driver, base_url):
    """TC-RESP-01: No horizontal page overflow at any width (375px, 768px, 1440px) on Coach, Admin, and Driver dashboards."""
    viewports = [
        (375, 812),   # Mobile (iPhone X / SE)
        (768, 1024),  # Tablet (iPad)
        (1440, 900),  # Desktop
    ]

    roles = [
        ("coach", COACH_CREDENTIALS, "/coach"),
        ("admin", ADMIN_CREDENTIALS, "/admin"),
        ("driver", DRIVER1_CREDENTIALS, "/driver"),
    ]

    login_page = LoginPage(driver, base_url)

    for role, creds, target_url in roles:
        driver.delete_all_cookies()
        login_page.open()
        login_page.login(
            role=role,
            identifier=creds["identifier"],
            password=creds["password"],
        )
        login_page.wait_for_url_contains(target_url)

        for width, height in viewports:
            driver.set_window_size(width, height)
            is_overflowing = driver.execute_script(
                "return (document.documentElement.scrollWidth > window.innerWidth + 2) || (document.body.scrollWidth > window.innerWidth + 2);"
            )
            assert not is_overflowing, f"Horizontal scroll overflow detected on {role} at viewport {width}x{height}"


def test_tc_resp_02_admin_user_table_transforms_to_cards_on_mobile(driver, base_url):
    """TC-RESP-02: Admin user table renders as cards below 768px and as a table at 1440px."""
    login_page = LoginPage(driver, base_url)
    admin_page = AdminDashboardPage(driver, base_url)

    login_page.open()
    login_page.login(
        role="admin",
        identifier=ADMIN_CREDENTIALS["identifier"],
        password=ADMIN_CREDENTIALS["password"],
    )
    admin_page.wait_for_url_contains("/admin")

    # 1. Desktop 1440px Viewport: Table must be visible, cards hidden
    driver.set_window_size(1440, 900)
    assert admin_page.is_user_table_displayed(), "Desktop table view not displayed at 1440px"
    assert not admin_page.is_user_cards_displayed(), "Mobile cards view unexpectedly displayed at 1440px"

    # 2. Mobile 375px Viewport: Cards must be visible, table hidden
    driver.set_window_size(375, 812)
    assert admin_page.is_user_cards_displayed(), "Mobile cards view not displayed at 375px"
    assert not admin_page.is_user_table_displayed(), "Desktop table view unexpectedly displayed at 375px"

    # Reset back to standard desktop viewport
    driver.set_window_size(1440, 900)


def test_tc_resp_03_desktop_timing_tower_and_sector_deltas_in_sidebar(driver, base_url):
    """TC-RESP-03: On desktop, Timing Tower and Sector Deltas are both inside right sidebar column (regression test for grid placement bug)."""
    login_page = LoginPage(driver, base_url)
    coach_page = CoachDashboardPage(driver, base_url)

    login_page.open()
    login_page.login(
        role="coach",
        identifier=COACH_CREDENTIALS["identifier"],
        password=COACH_CREDENTIALS["password"],
    )
    coach_page.wait_for_url_contains("/coach")

    driver.set_window_size(1440, 900)
    assert coach_page.is_sidebar_column_containing_panels(), (
        "Timing Tower and Sector Deltas are not both placed within the right sidebar column"
    )
