from selenium.webdriver.common.by import By
from .base_page import BasePage


class TopBar(BasePage):
    """Page Object for the persistent Shell TopBar component."""

    def get_role_badge(self) -> str:
        return self.get_text("topbar-role-badge")

    def get_user_badge(self) -> str:
        return self.get_text("topbar-user-badge")

    def open_settings(self):
        self.click("topbar-settings-btn")

    def sign_out(self):
        self.click("topbar-signout-btn")


class SettingsModal(BasePage):
    """Page Object for Settings modal."""

    def is_open(self, timeout: int = 3) -> bool:
        return self.is_visible("settings-modal", timeout=timeout)

    def set_font_size(self, size: str):
        size_key = size.lower().strip()
        testid = f"settings-font-size-{size_key}"
        self.click(testid)

    def get_root_font_size(self) -> str:
        return self.driver.execute_script("return document.documentElement.style.fontSize;")

    def has_theme_toggle(self) -> bool:
        """Regression test for removed theme toggle: ensures no theme toggle exists."""
        theme_matches = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid*="theme"]')
        return len(theme_matches) > 0

    def replay_tutorial(self):
        self.click("settings-replay-tutorial-btn")

    def close(self):
        if self.is_visible("settings-done-btn", timeout=2):
            self.click("settings-done-btn")
        else:
            self.click("settings-close-btn")
        self.wait_for_invisible("settings-modal")


class TutorialCallout(BasePage):
    """Page Object for onboarding tutorial callout."""

    def is_displayed(self, timeout: int = 3) -> bool:
        return self.is_visible("tutorial-callout", timeout=timeout)

    def get_step_title(self) -> str:
        return self.get_text("tutorial-step-title")

    def click_next(self):
        self.click("tutorial-next-btn")

    def click_skip(self):
        self.click("tutorial-skip-btn")

    def click_back(self):
        self.click("tutorial-back-btn")
