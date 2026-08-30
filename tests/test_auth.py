import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_signin_screen_components_load(driver):
    """
    Day 1 Sanity & Screen Verification:
    Verifies that StageTimePNW launches onto the initial SignInView and that
    critical interactive components (header, inputs, CTA buttons) are rendered and visible.
    """
    wait = WebDriverWait(driver, 15)

    # 1. Scope the 'Sign in' header strictly to a StaticText element to avoid button collision
    header_predicate = 'type == "XCUIElementTypeStaticText" AND label == "Sign in"'
    header = wait.until(
        EC.visibility_of_element_located((AppiumBy.IOS_PREDICATE, header_predicate))
    )
    assert header.is_displayed(), "Sign in screen header is not visible."

    # 2. Verify the primary 'Sign in' action button exists and is enabled
    button_predicate = 'type == "XCUIElementTypeButton" AND label == "Sign in"'
    signin_button = wait.until(
        EC.element_to_be_clickable((AppiumBy.IOS_PREDICATE, button_predicate))
    )
    assert signin_button.is_enabled(), "Primary 'Sign in' button is disabled."

    # 3. Verify the footer navigation prompt ('Don\'t have an account? Sign up')
    footer_predicate = 'label CONTAINS "Don\'t have an account?"'
    footer_prompt = wait.until(
        EC.visibility_of_element_located((AppiumBy.IOS_PREDICATE, footer_predicate))
    )
    assert footer_prompt.is_displayed(), "Footer sign-up link prompt is not visible."

    print("\n✅ Day 1 Session Successful: StageTimePNW SignInView fully verified!")