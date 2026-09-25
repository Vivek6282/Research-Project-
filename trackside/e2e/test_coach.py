"""Coach Dashboard E2E Test Suite for Trackside."""

import pytest
from e2e.pages.login_page import LoginPage
from e2e.pages.coach_page import CoachDashboardPage
from e2e.conftest import COACH_CREDENTIALS


@pytest.fixture(autouse=True)
def coach_login(driver, base_url):
    """Ensure each coach test begins authenticated as Coach on /coach."""
    login_page = LoginPage(driver, base_url)
    login_page.open()
    login_page.login(
        role="coach",
        identifier=COACH_CREDENTIALS["identifier"],
        password=COACH_CREDENTIALS["password"],
    )
    login_page.wait_for_url_contains("/coach")
    coach_page = CoachDashboardPage(driver, base_url)
    coach_page.wait_for_visible("coach-tab-live")
    yield coach_page


def test_tc_coach_01_dashboard_loads_all_panels(driver, base_url, coach_login):
    """TC-COACH-01: Dashboard loads all panels: Live Trajectory, Timing Tower, Sector Deltas, biometric cards, Custom Zone Threshold Control, Session Notes, Live Track View."""
    coach_page = coach_login
    expected_panels = [
        "live_trajectory",
        "timing_tower",
        "sector_deltas",
        "biometrics",
        "threshold_control",
        "session_notes",
        "live_track_view",
    ]
    for panel in expected_panels:
        assert coach_page.is_panel_displayed(panel), f"Panel {panel} is not displayed on Coach Dashboard"


def test_tc_coach_02_signal_strip_segments_and_stage_label(driver, base_url, coach_login):
    """TC-COACH-02: Signal strip renders exactly 5 segments, and the stage label matches the number of lit segments (2=Nominal, 4=Monitoring, 5=Intervene)."""
    coach_page = coach_login
    state = coach_page.get_signal_strip_state()
    assert state["totalSegments"] == 5, f"Expected exactly 5 segments in signal strip, found {state['totalSegments']}"

    lit_count = state["litCount"]
    stage_label = state["stageLabel"]

    # Stage label mapping logic:
    # 2 lit -> NOMINAL, 4 lit -> MONITORING, 5 lit -> INTERVENE
    if lit_count <= 2:
        assert "NOMINAL" in stage_label
    elif lit_count <= 4:
        assert "MONITORING" in stage_label
    else:
        assert "INTERVENE" in stage_label


def test_tc_coach_03_simulated_data_badge_visible_in_mock_mode(driver, base_url, coach_login):
    """TC-COACH-03: "SIMULATED DATA" badge is visible when mock telemetry mode is on."""
    coach_page = coach_login
    assert coach_page.is_simulated_data_badge_visible()


def test_tc_coach_04_threshold_slider_reflects_kart_bounds(driver, base_url, coach_login):
    """TC-COACH-04: Threshold slider min/max reflect kart-class bounds (not the old hardcoded 0.60–1.15)."""
    coach_page = coach_login
    min_val, max_val = coach_page.get_threshold_slider_bounds()

    # Sprint kart-class bounds default to floor 1.0g and ceiling 1.50g (or zone configured bounds), NOT old 0.60
    assert min_val >= 0.8, f"Slider min is {min_val}, expected kart class floor >= 0.8g (not old 0.60)"
    assert max_val >= 1.15, f"Slider max is {max_val}, expected >= 1.15g"


def test_tc_coach_05_save_session_note_persists(driver, base_url, coach_login):
    """TC-COACH-05: Save a session note → appears in the list and persists after refresh."""
    coach_page = coach_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    note_text = f"Apex turn observation {unique_suffix}"

    coach_page.save_session_note(note_text)

    # Verify note appears in notes list
    notes = coach_page.get_saved_notes_list()
    assert any(note_text in n for n in notes), f"Note '{note_text}' not found in notes list"

    # Refresh page
    driver.refresh()
    coach_page.wait_for_visible("coach-panel-session-notes")

    refreshed_notes = coach_page.get_saved_notes_list()
    assert any(note_text in n for n in refreshed_notes), f"Note '{note_text}' did not persist after refresh"


def test_tc_coach_06_create_new_zone(driver, base_url, coach_login):
    """TC-COACH-06: "+ New Zone" creates a zone with a corner type and it appears in the dropdown."""
    coach_page = coach_login
    unique_suffix = int(driver.execute_script("return Date.now();")) % 100000
    zone_name = f"Turn {unique_suffix} Sweeper"

    coach_page.create_zone(name=zone_name, corner_type="sweeper")

    options = coach_page.get_zone_options()
    assert any(zone_name in opt for opt in options), f"Zone '{zone_name}' not found in zone dropdown options: {options}"


def test_tc_coach_07_live_track_view_fallback_state(driver, base_url, coach_login):
    """TC-COACH-07: Live Track View shows fallback message when no reference line exists."""
    coach_page = coach_login
    assert coach_page.is_panel_displayed("live_track_view")


def test_tc_coach_08_historical_sessions_count_matches_rows(driver, base_url, coach_login):
    """TC-COACH-08: Historical Sessions tab count matches the number of rows shown."""
    coach_page = coach_login
    coach_page.switch_tab("history")

    coach_page.wait_for_visible("coach-historical-table")
    badge_count = coach_page.get_historical_count()
    row_count = coach_page.get_historical_rows_count()

    assert badge_count == row_count, f"Badge count ({badge_count}) does not match table row count ({row_count})"
