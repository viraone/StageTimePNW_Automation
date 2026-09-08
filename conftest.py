"""Shared pytest fixtures for the StageTimePNW iOS automation suite.

Environment knobs (all optional):

    STAGETIME_DEVICE_NAME        simulator name          (default: iPhone 17 Pro Max)
    STAGETIME_PLATFORM_VERSION   simulator iOS version   (default: 26.5)
    STAGETIME_BUNDLE_ID          app bundle id           (default: com.viradeth.StageTimePNW)
    STAGETIME_APP_PATH           path to a .app build; overrides the bundle id
    STAGETIME_APPIUM_URL         Appium server           (default: http://127.0.0.1:4723)
    STAGETIME_SUPABASE_URL       backend the app should talk to during the run,
                                 e.g. http://127.0.0.1:54321 for mock_supabase.py.
                                 Injected via processArguments.env (see
                                 docs/automation-guide.md, section 3a).
    STAGETIME_SUPABASE_ANON_KEY  anon key for the backend above (any string for the mock)
    STAGETIME_ARTIFACTS_DIR      where failure screenshots / page sources go (default: artifacts/)
"""
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

import urllib.error
import urllib.request

import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_TIMEOUT_S = 15
NETWORK_TIMEOUT_S = 30


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value else default


# --------------------------------------------------------------------------- #
# Backend                                                                      #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def backend_url() -> str | None:
    """Base URL of the auth backend the app is pointed at, or None for the
    app's compiled-in default (production)."""
    return _env("STAGETIME_SUPABASE_URL")


@pytest.fixture(scope="session")
def _warn_if_production(backend_url):
    if backend_url is None:
        import warnings

        warnings.warn(
            "STAGETIME_SUPABASE_URL is not set: sign-up tests will hit the app's "
            "compiled-in (production) Supabase project. Start `python mock_supabase.py` "
            "and export STAGETIME_SUPABASE_URL=http://127.0.0.1:54321.",
            stacklevel=1,
        )


@pytest.fixture
def reset_backend(backend_url):
    """Clear mock backend state so each test starts from a known baseline.
    No-op against a real Supabase instance."""
    is_local = backend_url and any(h in backend_url for h in ("127.0.0.1", "localhost"))
    if is_local:
        req = urllib.request.Request(f"{backend_url}/__reset", method="POST")
        try:
            urllib.request.urlopen(req, timeout=5).close()
        except (urllib.error.URLError, OSError):
            pass  # not the Flask mock; nothing to reset
    yield


# --------------------------------------------------------------------------- #
# Driver                                                                       #
# --------------------------------------------------------------------------- #
def _build_options(backend_url: str | None) -> XCUITestOptions:
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    options.device_name = _env("STAGETIME_DEVICE_NAME", "iPhone 17 Pro Max")
    options.platform_version = _env("STAGETIME_PLATFORM_VERSION", "26.5")

    app_path = _env("STAGETIME_APP_PATH")
    if app_path:
        options.app = app_path
    else:
        options.bundle_id = _env("STAGETIME_BUNDLE_ID", "com.viradeth.StageTimePNW")

    options.new_command_timeout = 300
    options.no_reset = False  # fresh install state; also required for processArguments.env

    if backend_url:
        options.set_capability(
            "appium:processArguments",
            {
                "env": {
                    "SUPABASE_URL": backend_url,
                    "SUPABASE_ANON_KEY": _env("STAGETIME_SUPABASE_ANON_KEY", "local-anon-key"),
                }
            },
        )
    return options


@pytest.fixture
def driver(request, backend_url, _warn_if_production, reset_backend):
    """One Appium session per test. On failure, dumps a screenshot and the
    XCUITest page source to the artifacts directory before quitting."""
    drv = webdriver.Remote(
        _env("STAGETIME_APPIUM_URL", "http://127.0.0.1:4723"),
        options=_build_options(backend_url),
    )
    try:
        yield drv
    finally:
        try:
            if getattr(request.node, "rep_call", None) and request.node.rep_call.failed:
                _capture_failure_artifacts(drv, request.node.nodeid)
        finally:
            drv.quit()


@pytest.fixture
def wait(driver) -> WebDriverWait:
    return WebDriverWait(driver, DEFAULT_TIMEOUT_S)


@pytest.fixture
def network_wait(driver) -> WebDriverWait:
    """Longer wait for steps that round-trip to the backend."""
    return WebDriverWait(driver, NETWORK_TIMEOUT_S)


# --------------------------------------------------------------------------- #
# Test data                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture
def unique_email() -> str:
    """Collision-free address per run. Uses a routable-looking domain so a real
    GoTrue instance will accept it (example.com is rejected by SMTP providers
    and surfaces as 'Error sending confirmation email')."""
    return f"stagetime.qa+{uuid.uuid4().hex[:12]}@stagetimepnw.test"


# --------------------------------------------------------------------------- #
# Failure artifacts                                                            #
# --------------------------------------------------------------------------- #
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def _capture_failure_artifacts(drv, nodeid: str) -> None:
    out_dir = Path(_env("STAGETIME_ARTIFACTS_DIR", "artifacts"))
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w.-]+", "_", nodeid)
    try:
        drv.save_screenshot(str(out_dir / f"{stem}.png"))
        (out_dir / f"{stem}.xml").write_text(drv.page_source, encoding="utf-8")
    except Exception as exc:  # never mask the real test failure
        print(f"[artifacts] could not capture failure state: {exc!r}")
