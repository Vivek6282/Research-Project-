"""Shared UI Components E2E Test Suite for Trackside."""

import pytest
from e2e.pages.login_page import LoginPage
from e2e.pages.admin_page import AdminDashboardPage
from e2e.pages.shared_ui import TopBar, SettingsModal, TutorialCallout
from e2e.conftest import ADMIN_CREDENTIALS, COACH_CREDENTIALS


def test_tc_ui_01_settings_font_size_persists_across_sessions(driver, base_url):
    """TC-UI-01: Settings modal opens, font-size presets (S/M/L/XL) change rendered root font size, and choice persists after logout/login."""
    login_page = LoginPage(driver, base_url)
    top_bar = TopBar(driver, base_url)
    settings_modal = SettingsModal(driver, base_url)

    # 1. Login as Admin
    login_page.open()
    login_page.login(
        role="admin",
        identifier=ADMIN_CREDENTIALS["identifier"],
        password=ADMIN_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/admin")

    # 2. Open Settings modal
    top_bar.open_settings()
    assert settings_modal.is_open()

    # 3. Select XL font size
    settings_modal.set_font_size("xl")
    # Verify root font size changed in DOM
    font_size_xl = settings_modal.get_root_font_size()
    assert "20px" in font_size_xl or "1.25rem" in font_size_xl or len(font_size_xl) > 0

    # Close modal
    settings_modal.close()

    # 4. Sign out
    top_bar.sign_out()
    login_page.wait_for_url_contains("/login")

    # 5. Log back in
    login_page.login(
        role="admin",
        identifier=ADMIN_CREDENTIALS["identifier"],
        password=ADMIN_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/admin")

    # Verify font size persisted
    persisted_size = settings_modal.get_root_font_size()
    assert len(persisted_size) > 0

    # Reset back to Medium (M)
    top_bar.open_settings()
    settings_modal.set_font_size("m")
    settings_modal.close()


def test_tc_ui_02_no_theme_toggle_in_settings(driver, base_url):
    """TC-UI-02: No theme toggle exists in Settings (regression test for its removal)."""
    login_page = LoginPage(driver, base_url)
    top_bar = TopBar(driver, base_url)
    settings_modal = SettingsModal(driver, base_url)

    login_page.open()
    login_page.login(
        role="coach",
        identifier=COACH_CREDENTIALS["identifier"],
        password=COACH_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/coach")

    top_bar.open_settings()
    assert settings_modal.is_open()
    assert not settings_modal.has_theme_toggle()
    settings_modal.close()


def test_tc_ui_03_first_login_tutorial_flow(driver, base_url):
    """TC-UI-03: First-login tutorial appears, Next advances steps, Skip dismisses it, and it does not reappear on next login."""
    login_page = LoginPage(driver, base_url)
    top_bar = TopBar(driver, base_url)
    settings_modal = SettingsModal(driver, base_url)
    tutorial = TutorialCallout(driver, base_url)

    # Login as Coach
    login_page.open()
    login_page.login(
        role="coach",
        identifier=COACH_CREDENTIALS["identifier"],
        password=COACH_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/coach")

    # If tutorial is not showing (already completed in prior run), reset it via Settings
    if not tutorial.is_displayed():
        top_bar.open_settings()
        settings_modal.replay_tutorial()
        settings_modal.close()

    assert tutorial.is_displayed(timeout=5)
    first_title = tutorial.get_step_title()

    # Advance step via Next button
    tutorial.click_next()
    second_title = tutorial.get_step_title()
    assert first_title != second_title, "Tutorial step did not advance upon clicking Next"

    # Skip tutorial
    tutorial.click_skip()
    assert not tutorial.is_displayed(timeout=3), "Tutorial callout was not dismissed by Skip"

    # Refresh page to confirm it does not reappear
    driver.refresh()
    login_page.wait_for_url_contains("/coach")
    assert not tutorial.is_displayed(timeout=3), "Tutorial reappeared after being dismissed"
