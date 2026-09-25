from typing import List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BasePage:
    """Base class for all Page Objects in Trackside E2E test suite.
    
    Enforces the rule that all interactions select by data-testid only,
    and all synchronization uses explicit WebDriverWait with expected_conditions.
    """

    def __init__(self, driver: WebDriver, base_url: str = "http://localhost:5173", default_timeout: int = 10):
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.default_timeout = default_timeout

    def _selector(self, testid: str) -> tuple:
        return (By.CSS_SELECTOR, f'[data-testid="{testid}"]')

    def open(self, path: str = ""):
        target_url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        self.driver.get(target_url)

    def wait_for_element(self, testid: str, timeout: int = None) -> WebElement:
        t = timeout or self.default_timeout
        return WebDriverWait(self.driver, t).until(
            EC.presence_of_element_located(self._selector(testid))
        )

    def wait_for_visible(self, testid: str, timeout: int = None) -> WebElement:
        t = timeout or self.default_timeout
        def _predicate(d):
            elements = d.find_elements(*self._selector(testid))
            for el in elements:
                if el.is_displayed():
                    return el
            return False
        return WebDriverWait(self.driver, t).until(_predicate)

    def wait_for_clickable(self, testid: str, timeout: int = None) -> WebElement:
        t = timeout or self.default_timeout
        def _predicate(d):
            elements = d.find_elements(*self._selector(testid))
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    return el
            return False
        return WebDriverWait(self.driver, t).until(_predicate)

    def wait_for_invisible(self, testid: str, timeout: int = None) -> bool:
        t = timeout or self.default_timeout
        return WebDriverWait(self.driver, t).until(
            EC.invisibility_of_element_located(self._selector(testid))
        )

    def find_elements(self, testid: str, timeout: int = 5) -> List[WebElement]:
        try:
            self.wait_for_element(testid, timeout=timeout)
            return self.driver.find_elements(*self._selector(testid))
        except TimeoutException:
            return []

    def click(self, testid: str, timeout: int = None):
        element = self.wait_for_clickable(testid, timeout=timeout)
        element.click()

    def type_text(self, testid: str, text: str, clear: bool = True, timeout: int = None):
        element = self.wait_for_visible(testid, timeout=timeout)
        if clear:
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.BACKSPACE)
            # Fallback clear in case input was empty or key combination didn't clear completely
            if element.get_attribute("value"):
                element.clear()
        element.send_keys(text)

    def get_text(self, testid: str, timeout: int = None) -> str:
        element = self.wait_for_visible(testid, timeout=timeout)
        return element.text

    def get_attribute(self, testid: str, attr_name: str, timeout: int = None) -> str:
        element = self.wait_for_element(testid, timeout=timeout)
        return element.get_attribute(attr_name)

    def is_visible(self, testid: str, timeout: int = 3) -> bool:
        try:
            self.wait_for_visible(testid, timeout=timeout)
            return True
        except TimeoutException:
            return False

    def is_present(self, testid: str, timeout: int = 3) -> bool:
        try:
            self.wait_for_element(testid, timeout=timeout)
            return True
        except TimeoutException:
            return False

    def wait_for_url_contains(self, substring: str, timeout: int = None):
        t = timeout or self.default_timeout
        WebDriverWait(self.driver, t).until(EC.url_contains(substring))

    def wait_for_url_matches(self, regex: str, timeout: int = None):
        t = timeout or self.default_timeout
        WebDriverWait(self.driver, t).until(EC.url_matches(regex))

    @property
    def current_url(self) -> str:
        return self.driver.current_url
