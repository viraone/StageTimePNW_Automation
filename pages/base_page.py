from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

Locator = tuple[str, str]


def by_id(accessibility_id: str) -> Locator:
    return (AppiumBy.ACCESSIBILITY_ID, accessibility_id)


def by_predicate(predicate: str) -> Locator:
    return (AppiumBy.IOS_PREDICATE, predicate)


def static_text(label: str) -> Locator:
    """Exact-label StaticText. Scoping by type avoids colliding with a Button
    that shares the same label (e.g. the 'Sign in' header vs. CTA)."""
    return by_predicate(f'type == "XCUIElementTypeStaticText" AND label == "{label}"')


class BasePage:
    DEFAULT_TIMEOUT_S = 15
    NETWORK_TIMEOUT_S = 30

    def __init__(self, driver, timeout: int = DEFAULT_TIMEOUT_S):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)
        self.network_wait = WebDriverWait(driver, self.NETWORK_TIMEOUT_S)

    # -- element access ----------------------------------------------------- #
    def find(self, locator: Locator | str):
        return self.wait.until(EC.visibility_of_element_located(self._loc(locator)))

    def tap(self, locator: Locator | str) -> None:
        self.wait.until(EC.element_to_be_clickable(self._loc(locator))).click()

    def type(self, locator: Locator | str, text: str):
        el = self.find(locator)
        el.click()
        el.clear()
        el.send_keys(text)
        return el

    def text_of(self, locator: Locator | str) -> str:
        return self.find(locator).text

    def is_present(self, locator: Locator | str, timeout: float = 0) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self._loc(locator))
            )
            return True
        except TimeoutException:
            return False

    def first_visible(self, *locators: Locator | str, wait: WebDriverWait | None = None):
        """Block until any of `locators` is visible; return (locator, element)."""
        resolved = [self._loc(l) for l in locators]

        def _any(driver):
            for loc in resolved:
                for el in driver.find_elements(*loc):
                    if el.is_displayed():
                        return loc, el
            return False

        return (wait or self.wait).until(_any)

    # -- keyboard ----------------------------------------------------------- #
    KEYBOARD = by_predicate('type == "XCUIElementTypeKeyboard"')
    RETURN_KEY = by_predicate(
        'type == "XCUIElementTypeButton" AND '
        '(name == "Return" OR name == "Done" OR name == "Go" OR name == "Next")'
    )

    def dismiss_keyboard(self) -> None:
        """Best-effort keyboard dismissal.

        WDA's native hide-keyboard only knows a few toolbar labels and raises
        InvalidElementStateException on plain SwiftUI keyboards. Work through
        the strategies the app actually supports; never fail the test here —
        callers tap elements that XCUITest scrolls into view regardless.
        """
        if not self._keyboard_visible():
            return
        for strategy in (self._hide_keyboard_native, self._tap_return_key, self._tap_outside_keyboard):
            try:
                strategy()
            except WebDriverException:
                continue
            if not self._keyboard_visible():
                return

    def _keyboard_visible(self) -> bool:
        try:
            return self.driver.is_keyboard_shown()
        except WebDriverException:
            return self.is_present(self.KEYBOARD)

    def _hide_keyboard_native(self) -> None:
        self.driver.hide_keyboard()

    def _tap_return_key(self) -> None:
        self.driver.find_element(*self.RETURN_KEY).click()

    def _tap_outside_keyboard(self) -> None:
        # Tap the top edge of the app window, well clear of the keyboard and
        # any interactive control, which resigns first responder in SwiftUI.
        size = self.driver.get_window_size()
        self.driver.execute_script(
            "mobile: tap", {"x": size["width"] // 2, "y": 40}
        )

    # -- helpers ------------------------------------------------------------ #
    @staticmethod
    def _loc(locator: Locator | str) -> Locator:
        return by_id(locator) if isinstance(locator, str) else locator
