import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions

@pytest.fixture(scope="function")
def driver():
    """setup and teardown for iOS simulator session."""
