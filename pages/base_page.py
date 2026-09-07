from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BasePage:
    def __init__(self, driver, timeout=15):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def find(self, accessibility_id):
        return self.wait.until(
            EC.visibility_of_element_located((AppiumBy.ACCESSIBILITY_ID, accessibility_id))
        )

    def tap(self, accessibility_id):
        self.wait.until(
            EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, accessibility_id))
        ).click()

    def type(self, accessibility_id, text):
        el = self.find(accessibility_id)
        el.click()
        el.clear()
        el.send_keys(text)
        return el

    def text_of(self, accessibility_id):
        return self.find(accessibility_id).text

    def dismiss_keyboard(self):
        if self.driver.is_keyboard_shown():
            self.driver.hide_keyboard()
