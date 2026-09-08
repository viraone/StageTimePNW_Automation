"""Page objects for the StageTimePNW authentication flow.

Locators prefer `accessibilityIdentifier`s (stable across copy changes). Where
the app has not yet tagged an element, a label-based fallback is provided and
flagged with `# TODO(app)` so the debt is visible.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from appium.webdriver.common.appiumby import AppiumBy

from .base_page import BasePage, by_id, by_predicate, static_text


class SignInPage(BasePage):
    HEADER = static_text("Sign in")
    SUBMIT = by_id("signin_submit_button")
    SIGNUP_PROMPT = static_text("Don't have an account?")
    TO_SIGNUP = by_id("signin_to_signup_link")

    def is_loaded(self) -> bool:
        return self.find(self.HEADER).is_displayed()

    def go_to_sign_up(self) -> "SignUpPage":
        self.tap(self.TO_SIGNUP)
        page = SignUpPage(self.driver)
        page.find(page.HEADER)
        return page


class SignUpOutcome(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True)
class SignUpResult:
    outcome: SignUpOutcome
    message: str

    @property
    def ok(self) -> bool:
        return self.outcome is SignUpOutcome.SUCCESS


class SignUpPage(BasePage):
    HEADER = static_text("Create your account")  # TODO(app): signup_header_title
    EMAIL = by_id("signup_email_input")
    PASSWORD = by_id("signup_password_input")
    CONFIRM = by_id("signup_confirm_password_input")
    SUBMIT = by_id("signup_submit_button")
    TO_SIGNIN = by_predicate('type == "XCUIElementTypeButton" AND label == "Log In"')  # TODO(app): signup_to_signin_link

    # Scoped to StaticText: AuthView sets the identifier on the HStack, and
    # SwiftUI propagates it to the icon Image too (whose value is "Selected").
    # TODO(app): add .accessibilityElement(children: .combine) to that HStack.
    SUCCESS = by_predicate(
        'type == "XCUIElementTypeStaticText" AND name == "signup_success_message"'
    )
    ERROR = by_predicate(
        'type == "XCUIElementTypeStaticText" AND name == "signup_error_message"'
    )
    # TODO(app): remove once AuthView tags the error/success Text views. Until then
    # the error surfaces as an untagged StaticText next to a warning icon.
    ERROR_FALLBACK = by_predicate(
        'type == "XCUIElementTypeStaticText" AND '
        '(label CONTAINS[c] "error" OR label CONTAINS[c] "invalid" OR '
        'label CONTAINS[c] "must" OR label CONTAINS[c] "please")'
    )
    SUCCESS_FALLBACK = by_predicate(
        'type == "XCUIElementTypeStaticText" AND '
        '(label CONTAINS[c] "account created" OR label CONTAINS[c] "check your email")'
    )

    def is_loaded(self) -> bool:
        return self.find(self.HEADER).is_displayed()

    def fill(self, email: str, password: str, confirm: str | None = None) -> "SignUpPage":
        self.type(self.EMAIL, email)
        self.type(self.PASSWORD, password)
        self.type(self.CONFIRM, password if confirm is None else confirm)
        self.dismiss_keyboard()
        return self

    def submit(self) -> "SignUpPage":
        self.tap(self.SUBMIT)
        return self

    def sign_up(self, email: str, password: str, confirm: str | None = None) -> "SignUpPage":
        return self.fill(email, password, confirm).submit()

    def wait_for_result(self) -> SignUpResult:
        """Block until the app renders either a success or an error message.

        Raises TimeoutException (with a clear diagnosis) if neither appears,
        which means the form never submitted or the app hung.
        """
        locator, element = self.first_visible(
            self.SUCCESS, self.ERROR, self.SUCCESS_FALLBACK, self.ERROR_FALLBACK,
            wait=self.network_wait,
        )
        outcome = (
            SignUpOutcome.SUCCESS
            if locator in (self.SUCCESS, self.SUCCESS_FALLBACK)
            else SignUpOutcome.ERROR
        )
        return SignUpResult(outcome, self._message_text(element))

    def _message_text(self, element) -> str:
        """Resolve human-readable copy regardless of where the identifier sits.

        iOS `.text` returns `value` first, which for a tagged container or a
        selected Text is the literal "Selected". Prefer the label, then any
        descendant StaticText labels, then fall back to the raw value.
        """
        label = (element.get_attribute("label") or "").strip()
        if label and label.lower() != "selected":
            return label
        children = element.find_elements(
            AppiumBy.IOS_CLASS_CHAIN, "**/XCUIElementTypeStaticText"
        )
        parts = [(c.get_attribute("label") or c.text or "").strip() for c in children]
        joined = " ".join(p for p in parts if p and p.lower() != "selected")
        return joined or (element.text or "").strip()

    # Convenience accessors kept for the existing test_signup.py suite.
    def success_text(self) -> str:
        return self.text_of(self.SUCCESS)

    def error_text(self) -> str:
        return self.text_of(self.ERROR)
