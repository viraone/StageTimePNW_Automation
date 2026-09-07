import time
import pytest
from pages.auth_page import SignInPage


@pytest.fixture
def unique_email():
    return f"qa+{int(time.time())}@stagetimepnw.test"


def test_signup_happy_path_shows_verification_message(driver, unique_email):
    """Sign in -> Sign up -> valid form -> 'check your email' confirmation.
    Needs a local Supabase or the mock backend (docs/automation-guide.md, section 2)."""
    signup = SignInPage(driver).go_to_sign_up()
    assert signup.is_loaded()

    signup.sign_up(unique_email, "Passw0rd!")

    msg = signup.success_text()
    assert "Account created" in msg
    assert unique_email in msg, "Success message should echo the email used"


def test_signup_rejects_short_password(driver, unique_email):
    signup = SignInPage(driver).go_to_sign_up()
    signup.sign_up(unique_email, "12345")
    assert signup.error_text() == "Password must be at least 6 characters."


def test_signup_rejects_mismatched_passwords(driver, unique_email):
    signup = SignInPage(driver).go_to_sign_up()
    signup.sign_up(unique_email, "Passw0rd!", confirm="Passw0rd?")
    assert signup.error_text() == "Passwords do not match."


def test_signup_rejects_empty_email(driver):
    signup = SignInPage(driver).go_to_sign_up()
    signup.sign_up("", "Passw0rd!")
    assert signup.error_text() == "Please enter your email address."
