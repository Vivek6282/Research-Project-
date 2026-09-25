from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from .base_page import BasePage


class AdminDashboardPage(BasePage):
    """Page Object for Trackside Admin Dashboard (/admin)."""

    def open(self):
        super().open("/admin")
        self.wait_for_visible("admin-user-management-panel")

    def click_add_account(self):
        self.click("admin-add-account-btn")

    def fill_create_account(self, name: str, role: str, email: str = "", password: str = ""):
        self.type_text("admin-create-name-input", name)
        role_select = self.wait_for_element("admin-create-role-select")
        for option in role_select.find_elements(By.TAG_NAME, "option"):
            if option.get_attribute("value") == role.lower():
                option.click()
                break
        if email:
            self.type_text("admin-create-email-input", email)
        if password:
            self.type_text("admin-create-password-input", password)

    def submit_create_account(self):
        self.click("admin-create-submit-btn")

    def create_user(self, name: str, role: str, email: str = "", password: str = "AdminPassword123!"):
        self.click_add_account()
        self.fill_create_account(name=name, role=role, email=email, password=password)
        self.submit_create_account()

    def get_create_error(self, timeout: int = 5) -> str:
        return self.get_text("admin-create-error", timeout=timeout)

    def is_create_error_displayed(self, timeout: int = 3) -> bool:
        return self.is_visible("admin-create-error", timeout=timeout)

    def get_created_success_username(self, timeout: int = 10) -> str:
        return self.get_text("admin-create-success-username", timeout=timeout)

    def is_create_success_displayed(self, timeout: int = 5) -> bool:
        return self.is_visible("admin-create-success", timeout=timeout)

    def get_user_row_elements(self) -> List:
        return self.find_elements("admin-user-row")

    def find_user_id_by_name(self, name: str, timeout: int = 10) -> Optional[str]:
        t = timeout or self.default_timeout
        def _predicate(d):
            rows = d.find_elements(*self._selector("admin-user-row"))
            for r in rows:
                if name.lower() in r.text.lower():
                    return r.get_attribute("data-user-id")
            return False

        try:
            return WebDriverWait(self.driver, t).until(_predicate)
        except TimeoutException:
            return None

    def get_user_status(self, user_id: str) -> str:
        return self.get_text(f"admin-user-status-{user_id}")

    def click_edit_user(self, user_id: str):
        self.click(f"admin-user-edit-btn-{user_id}")

    def fill_and_save_edit(self, new_name: str = None, new_email: str = None):
        if new_name is not None:
            self.type_text("admin-edit-name-input", new_name)
        if new_email is not None:
            self.type_text("admin-edit-email-input", new_email)
        self.click("admin-edit-save-btn")
        self.wait_for_invisible("admin-edit-save-btn")

    def click_deactivate_or_reactivate(self, user_id: str):
        self.click(f"admin-user-deactivate-btn-{user_id}")

    def confirm_dialog_confirm(self):
        self.click("confirm-dialog-confirm-btn")
        self.wait_for_invisible("confirm-dialog")

    def confirm_dialog_cancel(self):
        self.click("confirm-dialog-cancel-btn")

    def is_confirm_dialog_displayed(self, timeout: int = 3) -> bool:
        return self.is_visible("confirm-dialog", timeout=timeout)

    def has_delete_button(self) -> bool:
        """Regression test for removed hard-delete feature: ensures no delete button exists."""
        delete_matches = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid*="delete"]')
        return len(delete_matches) > 0

    def get_audit_log_entries(self) -> List[str]:
        elements = self.find_elements("admin-audit-log-entry")
        return [el.text for el in elements]

    def click_run_diagnostic(self):
        self.click("admin-run-diagnostic-btn")

    def is_diagnostic_waiting(self, timeout: int = 5) -> bool:
        return self.is_visible("admin-diagnostic-waiting", timeout=timeout)

    def is_user_table_displayed(self) -> bool:
        return self.is_visible("admin-user-table", timeout=3)

    def is_user_cards_displayed(self) -> bool:
        return self.is_visible("admin-user-cards-container", timeout=3)
