from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from .base_page import BasePage


class CoachDashboardPage(BasePage):
    """Page Object for Trackside Coach Dashboard (/coach)."""

    def open(self):
        super().open("/coach")
        self.wait_for_visible("coach-tab-live")

    def switch_tab(self, tab: str):
        if tab == "live":
            self.click("coach-tab-live")
        elif tab == "history":
            self.click("coach-tab-history")

    def is_panel_displayed(self, panel_name: str) -> bool:
        panel_map = {
            "live_trajectory": "coach-panel-live-trajectory",
            "timing_tower": "coach-panel-timing-tower",
            "corner_deltas": "coach-panel-corner-deltas",
            "biometrics": "coach-panel-biometrics",
            "session_notes": "coach-panel-session-notes",
            "live_track_view": "coach-panel-live-track-view",
        }
        testid = panel_map.get(panel_name, panel_name)
        return self.is_visible(testid)

    def get_signal_strip_segments(self) -> List:
        return self.find_elements("coach-signal-strip-segment-0") + \
               self.find_elements("coach-signal-strip-segment-1") + \
               self.find_elements("coach-signal-strip-segment-2") + \
               self.find_elements("coach-signal-strip-segment-3") + \
               self.find_elements("coach-signal-strip-segment-4")

    def get_signal_strip_segment_elements(self) -> List:
        return self.driver.find_elements(By.CSS_SELECTOR, '[data-testid^="coach-signal-strip-segment-"]')

    def get_signal_strip_state(self) -> dict:
        return self.driver.execute_script("""
            const segments = Array.from(document.querySelectorAll('[data-testid^="coach-signal-strip-segment-"]'));
            const lit = segments.filter(el => el.getAttribute('data-lit') === 'true').length;
            const labelEl = document.querySelector('[data-testid="coach-signal-strip-stage-label"]');
            return {
                totalSegments: segments.length,
                litCount: lit,
                stageLabel: labelEl ? labelEl.innerText.trim().toUpperCase() : ''
            };
        """)

    def get_signal_strip_lit_count(self) -> int:
        return self.get_signal_strip_state()["litCount"]

    def get_signal_strip_stage_label(self) -> str:
        return self.get_signal_strip_state()["stageLabel"]

    def is_simulated_data_badge_visible(self) -> bool:
        return self.is_visible("coach-simulated-data-badge", timeout=3)

    def save_session_note(self, text: str):
        self.type_text("coach-note-input", text)
        self.click("coach-save-note-btn")
        # Wait until the input has been cleared by React after successful save
        WebDriverWait(self.driver, self.default_timeout).until(
            lambda d: d.find_element(By.CSS_SELECTOR, '[data-testid="coach-note-input"]').get_attribute("value") == ""
        )

    def get_saved_notes_list(self, timeout: int = 10) -> List[str]:
        try:
            self.wait_for_visible("coach-note-item", timeout=timeout)
        except Exception:
            pass
        items = self.find_elements("coach-note-item")
        return [item.text for item in items]

    def create_zone(self, name: str, corner_type: str = "hairpin"):
        select_el = self.wait_for_element("coach-zone-select")
        Select(select_el).select_by_value("__new__")

        self.wait_for_visible("coach-new-zone-form")
        self.type_text("coach-new-zone-name-input", name)
        corner_select = self.wait_for_element("coach-new-zone-corner-select")
        Select(corner_select).select_by_value(corner_type.lower())
        self.click("coach-new-zone-add-btn")
        self.wait_for_invisible("coach-new-zone-form")

    def get_zone_options(self) -> List[str]:
        select_el = self.wait_for_element("coach-zone-select")
        return [opt.text for opt in Select(select_el).options]

    def is_live_track_fallback_displayed(self) -> bool:
        return self.is_visible("live-track-fallback", timeout=3)

    def get_historical_count(self) -> int:
        text = self.get_text("coach-historical-count")
        # e.g. "4 SESSIONS RECORDED"
        import re
        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else 0

    def get_historical_rows_count(self) -> int:
        rows = self.find_elements("coach-historical-row")
        return len(rows)

    def is_sidebar_column_containing_panels(self) -> bool:
        """Regression test for grid placement bug: Timing Tower and Corner Deltas are inside sidebar."""
        sidebar = self.wait_for_element("coach-sidebar-column")
        tt_inside = len(sidebar.find_elements(By.CSS_SELECTOR, '[data-testid="coach-panel-timing-tower"]')) > 0
        cd_inside = len(sidebar.find_elements(By.CSS_SELECTOR, '[data-testid="coach-panel-corner-deltas"]')) > 0
        return tt_inside and cd_inside
