import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions

@pytest.fixture(scope="function")
def driver():
    """setup and teardown for iOS simulator session."""

    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    
    # 📱 Match these to your simulator setup:
    options.device_name = "iPhone 17 Pro Max"  # Or your active simulator name
    options.platform_version = "26.5"          # Your simulator iOS version

    # 📦 Option A: If the app is already installed on simulator, use its Bundle ID:
    options.bundle_id = "com.viradeth.StageTimePNW"
    
    # 📦 Option B: If pointing directly to the build output (.app file):
    # options.app = "/path/to/your/build/StageTimePNW.app"

    options.new_command_timeout = 300
    options.no_reset = False

    # Connect to the local Appium server
    appium_server_url = "http://127.0.0.1:4723"
    driver = webdriver.Remote(appium_server_url, options=options)
    
    yield driver  # This runs the test
    
    # Teardown: close session after test completes
    driver.quit()


    
