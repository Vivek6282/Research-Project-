from .base_page import BasePage


class LoginPage(BasePage):
    """Page Object for Trackside Login Portal (/login)."""

    def open(self):
        super().open("/login")
        self.wait_for_visible("login-form")

    def select_role(self, role: str):
        role_normalized = role.lower().strip()
        testid = f"login-role-tab-{role_normalized}"
        self.click(testid)

    def enter_identifier(self, identifier: str):
        self.type_text("login-identifier-input", identifier)

    def enter_password(self, password: str):
        self.type_text("login-password-input", password)

    def submit(self):
        self.click("login-submit-btn")

    def login(self, role: str, identifier: str, password: str):
        self.select_role(role)
        self.enter_identifier(identifier)
        self.enter_password(password)
        self.submit()

    def get_error_message(self, timeout: int = 5) -> str:
        return self.get_text("login-error", timeout=timeout)

    def is_error_displayed(self, timeout: int = 3) -> bool:
        return self.is_visible("login-error", timeout=timeout)

    def is_login_form_displayed(self) -> bool:
        return self.is_visible("login-form")
