from .base_page import BasePage


class SignInPage(BasePage):
    HEADER = "signin_header_title"
    TO_SIGNUP = "signin_to_signup_link"

    def is_loaded(self):
        return self.find(self.HEADER).is_displayed()

    def go_to_sign_up(self):
        self.tap(self.TO_SIGNUP)
        return SignUpPage(self.driver)


class SignUpPage(BasePage):
    """Requires the signup_* accessibilityIdentifiers in AuthView.swift
    (see docs/automation-guide.md, section 3b)."""

    HEADER = "signup_header_title"
    EMAIL = "signup_email_input"
    PASSWORD = "signup_password_input"
    CONFIRM = "signup_confirm_password_input"
    SUBMIT = "signup_submit_button"
    SUCCESS = "signup_success_message"
    ERROR = "signup_error_message"

    def is_loaded(self):
        return self.find(self.HEADER).is_displayed()

    def sign_up(self, email, password, confirm=None):
        self.type(self.EMAIL, email)
        self.type(self.PASSWORD, password)
        self.type(self.CONFIRM, password if confirm is None else confirm)
        self.dismiss_keyboard()
        self.tap(self.SUBMIT)
        return self

    def success_text(self):
        return self.text_of(self.SUCCESS)

    def error_text(self):
        return self.text_of(self.ERROR)
