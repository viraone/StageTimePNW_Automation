"""Sanity and happy-path coverage for the StageTimePNW authentication screens.

Preconditions
-------------
* Appium server running; simulator matches conftest defaults (or override via
  STAGETIME_* env vars).
* For `test_successful_signup_flow`: point the app at a disposable backend
  (`python mock_supabase.py` + `STAGETIME_SUPABASE_URL=http://127.0.0.1:54321`).
  Against production, Supabase must be able to deliver a confirmation email or
  it responds with "Error sending confirmation email".
"""
import pytest

from pages.auth_page import SignInPage

# Meets the app's password requirements.
# This is test data, not a credential for an existing account.
VALID_PASSWORD = "TestPass123!"


@pytest.mark.smoke
def test_signin_screen_components_load(driver):
    """Sign-in screen renders its header, primary CTA, and sign-up prompt."""
    signin = SignInPage(driver)

    assert signin.is_loaded(), "Sign-in header not visible on launch"
    assert signin.find(signin.SUBMIT).is_enabled(), "Primary 'Sign in' button is disabled"
    assert signin.find(signin.SIGNUP_PROMPT).is_displayed(), "Sign-up prompt not visible"
    assert signin.find(signin.TO_SIGNUP).is_enabled(), "Sign-up link is disabled"


@pytest.mark.signup
def test_successful_signup_flow(driver, unique_email):
    """Navigate to signup, submit valid details, and check confirmation.

    # Perform our own navigation so this test can run independently
    # of the sign-in smoke test.
    """
    signup = SignInPage(driver).go_to_sign_up()
    assert signup.is_loaded(), "Did not navigate to 'Create your account'"

    # unique_email is supplied by a fixture to avoid reusing the same
    # address across runs.
    #
    # The page object's sign_up() helper handles form entry and submission.
    # It should fill email, password, and matching confirm password,
    # then tap Create Account.
    #
    # wait_for_result() should wait for either success or an app error,
    # allowing rejections to report their message instead of timing out.

    # Fail with the returned message if signup was rejected.
    result = signup.sign_up(unique_email, VALID_PASSWORD).wait_for_result()

    assert result.ok, f"Sign-up rejected by backend: {result.message!r}"

    # Verify that the confirmation refers to this run's submitted email.
    assert unique_email in result.message, (
        f"Success message should echo the registered email; got {result.message!r}"
    )
