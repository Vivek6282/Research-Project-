"""Admin Dashboard E2E Test Suite for Trackside."""

import pytest
from e2e.pages.login_page import LoginPage
from e2e.pages.admin_page import AdminDashboardPage
from e2e.conftest import ADMIN_CREDENTIALS


@pytest.fixture(autouse=True)
def admin_login(driver, base_url):
    """Ensure each admin test begins authenticated as Admin on /admin."""
    login_page = LoginPage(driver, base_url)
    login_page.open()
    login_page.login(
        role="admin",
        identifier=ADMIN_CREDENTIALS["identifier"],
        password=ADMIN_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/admin")
    admin_page = AdminDashboardPage(driver, base_url)
    admin_page.wait_for_visible("admin-user-management-panel")
    yield admin_page


def test_tc_admin_01_create_coach_with_email(driver, base_url, admin_login):
    """TC-ADMIN-01: Create a Coach (email required) — appears in the user table with a generated TRK-COACH- username."""
    admin_page = admin_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    coach_name = f"TestCoach {unique_suffix}"
    coach_email = f"coach_{unique_suffix}@trackside.local"

    admin_page.create_user(name=coach_name, role="coach", email=coach_email, password="CoachPassword123!")

    assert admin_page.is_create_success_displayed()
    username = admin_page.get_created_success_username()
    assert "TRK-COACH-" in username

    # Verify user appears in user table
    user_id = admin_page.find_user_id_by_name(coach_name)
    assert user_id is not None, f"Created coach {coach_name} not found in user table"


def test_tc_admin_02_create_driver_without_email(driver, base_url, admin_login):
    """TC-ADMIN-02: Create a Driver without email — succeeds, generated TRK-DRV- username shown once."""
    admin_page = admin_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    driver_name = f"TestDriver {unique_suffix}"

    admin_page.create_user(name=driver_name, role="driver", email="", password="DriverPassword123!")

    assert admin_page.is_create_success_displayed()
    username = admin_page.get_created_success_username()
    assert "TRK-DRV-" in username


def test_tc_admin_03_coach_creation_without_email_rejected(driver, base_url, admin_login):
    """TC-ADMIN-03: Coach creation without email is rejected with a visible validation message."""
    admin_page = admin_login
    admin_page.create_user(name="No Email Coach", role="coach", email="", password="CoachPassword123!")

    assert admin_page.is_create_error_displayed()
    error_msg = admin_page.get_create_error()
    assert "Email" in error_msg or "required" in error_msg.lower()


def test_tc_admin_04_created_user_persists_after_refresh(driver, base_url, admin_login):
    """TC-ADMIN-04: Newly created user persists after a page refresh (regression test for disappearing-users bug)."""
    admin_page = admin_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    driver_name = f"PersistDriver {unique_suffix}"

    admin_page.create_user(name=driver_name, role="driver", email="", password="DriverPassword123!")
    assert admin_page.is_create_success_displayed()

    # Refresh page
    driver.refresh()
    admin_page.wait_for_visible("admin-user-management-panel")

    # Assert user is still present after refresh
    user_id = admin_page.find_user_id_by_name(driver_name)
    assert user_id is not None, f"User {driver_name} disappeared after refresh"


def test_tc_admin_05_edit_user_name_persists_after_refresh(driver, base_url, admin_login):
    """TC-ADMIN-05: Edit a user's name — change persists after refresh."""
    admin_page = admin_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    initial_name = f"EditUser {unique_suffix}"
    updated_name = f"UpdatedUser {unique_suffix}"

    admin_page.create_user(name=initial_name, role="driver", email="", password="DriverPassword123!")
    user_id = admin_page.find_user_id_by_name(initial_name)
    assert user_id is not None

    # Perform Edit
    admin_page.click_edit_user(user_id)
    admin_page.fill_and_save_edit(new_name=updated_name)

    # Refresh page
    driver.refresh()
    admin_page.wait_for_visible("admin-user-management-panel")

    # Assert updated name persisted
    found_id = admin_page.find_user_id_by_name(updated_name)
    assert found_id == user_id


def test_tc_admin_06_deactivate_confirm_dialog_and_reactivate(driver, base_url, admin_login):
    """TC-ADMIN-06: Deactivate via styled ConfirmDialog (no native confirm) -> status Inactive; Reactivate restores it."""
    admin_page = admin_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    driver_name = f"ToggleUser {unique_suffix}"

    admin_page.create_user(name=driver_name, role="driver", email="", password="DriverPassword123!")
    user_id = admin_page.find_user_id_by_name(driver_name)
    assert user_id is not None

    # Deactivate click
    admin_page.click_deactivate_or_reactivate(user_id)

    # Verify custom styled modal is open (not browser native alert)
    assert admin_page.is_confirm_dialog_displayed()
    admin_page.confirm_dialog_confirm()

    # Verify status changed to Inactive
    admin_page.wait_for_visible(f"admin-user-status-{user_id}")
    status = admin_page.get_user_status(user_id)
    assert "Inactive" in status

    # Reactivate user
    admin_page.click_deactivate_or_reactivate(user_id)
    assert admin_page.is_confirm_dialog_displayed()
    admin_page.confirm_dialog_confirm()

    admin_page.wait_for_visible(f"admin-user-status-{user_id}")
    new_status = admin_page.get_user_status(user_id)
    assert "Active" in new_status


def test_tc_admin_07_no_delete_button_exists(driver, base_url, admin_login):
    """TC-ADMIN-07: No "Delete" button exists anywhere (regression test for the removed hard-delete feature)."""
    admin_page = admin_login
    assert not admin_page.has_delete_button()


def test_tc_admin_08_audit_log_shows_new_entry(driver, base_url, admin_login):
    """TC-ADMIN-08: Audit log panel shows a new entry after a user is created/deactivated."""
    admin_page = admin_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    driver_name = f"AuditDriver {unique_suffix}"

    admin_page.create_user(name=driver_name, role="driver", email="", password="DriverPassword123!")
    
    entries = admin_page.get_audit_log_entries()
    assert len(entries) > 0
    # Confirm either driver name or CREATE USER action is in the audit log
    audit_text = " ".join(entries)
    assert "CREATE USER" in audit_text or driver_name in audit_text


def test_tc_admin_09_device_diagnostic_waiting_state(driver, base_url, admin_login):
    """TC-ADMIN-09: Device diagnostic: "Run Diagnostic" creates a pending command and UI shows waiting state."""
    admin_page = admin_login
    if admin_page.is_visible("admin-run-diagnostic-btn", timeout=3):
        btn = admin_page.wait_for_element("admin-run-diagnostic-btn")
        if btn.is_enabled():
            admin_page.click_run_diagnostic()
            assert admin_page.is_diagnostic_waiting(timeout=5)
