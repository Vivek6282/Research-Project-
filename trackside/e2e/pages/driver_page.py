from .base_page import BasePage
from e2e.timeouts import ABSENCE_TIMEOUT_S


class DriverDashboardPage(BasePage):
    """Page Object for Trackside Driver Dashboard (/driver)."""

    def open(self):
        super().open("/driver")
        self.wait_for_visible("driver-panel-telemetry")

    def is_no_sessions_displayed(self) -> bool:
        return self.is_visible("driver-no-sessions-msg")

    def toggle_mode(self, mode: str):
        mode_norm = mode.lower().strip()
        if mode_norm == "safety":
            self.click("driver-mode-safety-btn")
        elif mode_norm == "performance":
            self.click("driver-mode-performance-btn")

    def get_active_mode_text(self) -> str:
        return self.get_text("driver-active-mode-text")

    def is_panel_displayed(self, panel_name: str) -> bool:
        panel_map = {
            "telemetry": "driver-panel-telemetry",
            "mode": "driver-panel-mode",
            "zone_heatmap": "driver-panel-zone-heatmap",
            "best_lap": "driver-panel-best-lap",
            "target_evaluation": "driver-panel-target-evaluation",
        }
        testid = panel_map.get(panel_name, panel_name)
        return self.is_visible(testid)

    def is_phase_1_5_banner_displayed(self) -> bool:
        return self.is_visible("dev-banner-phase-1.5") or self.is_visible("dev-banner-phase-1-5", timeout=ABSENCE_TIMEOUT_S)

    def is_phase_2_banner_displayed(self) -> bool:
        return self.is_visible("dev-banner-phase-2")

    def get_signal_strip_stage_label(self) -> str:
        return self.get_text("driver-signal-strip-stage-label")
