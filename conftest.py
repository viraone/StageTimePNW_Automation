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
# Lets `str | None` annotations work on older Python versions by deferring the
# evaluation of every annotation in this module to a string.
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

# Stdlib HTTP is enough to poke the mock backend; avoids a `requests` dependency.
import urllib.error
import urllib.request

import pytest
from appium import webdriver

# Capability builder for Appium's iOS driver (XCUITest = Apple's UI test engine).
from appium.options.ios import XCUITestOptions

# Polling helper: retries a condition until it passes or the timeout expires.
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_TIMEOUT_S = 15   # normal UI waits (a view appearing, a button enabling)
NETWORK_TIMEOUT_S = 30   # waits that include a backend round-trip


def _env(name: str, default: str | None = None) -> str | None:
    """Read an env var, treating an empty string the same as unset.

    Plain `os.environ.get(name, default)` would return "" for `FOO=`, which then
    silently overrides the default with a useless value. This collapses both the
    missing and the blank case onto `default`.
    """
    value = os.environ.get(name)
    return value if value else default


# --------------------------------------------------------------------------- #
# Backend                                                                      #
# --------------------------------------------------------------------------- #
# Session-scoped: resolved once for the whole run, not per test.
@pytest.fixture(scope="session")
def backend_url() -> str | None:
    """Base URL of the auth backend the app is pointed at, or None for the
    app's compiled-in default (production)."""
    return _env("STAGETIME_SUPABASE_URL")


# Session-scoped so the warning is emitted once per run rather than once per test.
# Underscore-prefixed because tests never request it directly -- the `driver`
# fixture pulls it in as a dependency purely for the side effect.
@pytest.fixture(scope="session")
def _warn_if_production(backend_url):
    # No override set => the app will use whatever Supabase project it was built
    # with. Sign-up tests would then create real users, so make that loud.
    if backend_url is None:
        import warnings

        warnings.warn(
            "STAGETIME_SUPABASE_URL is not set: sign-up tests will hit the app's "
            "compiled-in (production) Supabase project. Start `python mock_supabase.py` "
            "and export STAGETIME_SUPABASE_URL=http://127.0.0.1:54321.",
            stacklevel=1,
        )


# Function-scoped (the default): runs fresh before every test that uses it.
@pytest.fixture
def reset_backend(backend_url):
    """Clear mock backend state so each test starts from a known baseline.
    No-op against a real Supabase instance."""
    # Only ever wipe something running on this machine -- a loopback host is the
    # guard that stops `/__reset` from being fired at a shared/staging backend.
    is_local = backend_url and any(h in backend_url for h in ("127.0.0.1", "localhost"))
    if is_local:
        # `/__reset` is an endpoint mock_supabase.py exposes; it drops the
        # in-memory user table so a re-used email counts as new again.
        req = urllib.request.Request(f"{backend_url}/__reset", method="POST")
        try:
            urllib.request.urlopen(req, timeout=5).close()
        except (urllib.error.URLError, OSError):
            pass  # not the Flask mock; nothing to reset
    # Everything above is setup; the bare yield hands control to the test and
    # means there is no teardown to perform afterwards.
    yield


# --------------------------------------------------------------------------- #
# Driver                                                                       #
# --------------------------------------------------------------------------- #
def _build_options(backend_url: str | None) -> XCUITestOptions:
    """Assemble the capability payload Appium uses to pick a simulator and app."""
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    # Device name + platform version together select which simulator boots; both
    # must match one that `xcrun simctl list` actually reports.
    options.device_name = _env("STAGETIME_DEVICE_NAME", "iPhone 17 Pro Max")
    options.platform_version = _env("STAGETIME_PLATFORM_VERSION", "26.5")

    # Two ways to say "which app": install a build from disk, or launch one that
    # is already installed on the simulator. A supplied path wins.
    app_path = _env("STAGETIME_APP_PATH")
    if app_path:
        options.app = app_path
    else:
        options.bundle_id = _env("STAGETIME_BUNDLE_ID", "com.viradeth.StageTimePNW")

    # How long Appium keeps the session alive between commands before deciding
    # the client went away. 300s absorbs slow simulator boots and debugging pauses.
    options.new_command_timeout = 300
    options.no_reset = False  # fresh install state; also required for processArguments.env

    if backend_url:
        # processArguments.env is the hand-off point: these become environment
        # variables inside the app process at launch, so the app reads them
        # instead of its compiled-in Supabase config and talks to the mock.
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


# Requesting `_warn_if_production` and `reset_backend` here means every test that
# asks for a driver automatically gets the production warning and the mock reset,
# in that order, without having to name those fixtures itself.
@pytest.fixture
def driver(request, backend_url, _warn_if_production, reset_backend):
    """One Appium session per test. On failure, dumps a screenshot and the
    XCUITest page source to the artifacts directory before quitting."""
    # Opens the WebDriver session: boots/attaches to the simulator, installs or
    # launches the app, and returns the handle tests drive the UI through.
    drv = webdriver.Remote(
        _env("STAGETIME_APPIUM_URL", "http://127.0.0.1:4723"),
        options=_build_options(backend_url),
    )
    try:
        yield drv  # the test body runs here
    finally:
        # Nested try/finally so a failure while capturing artifacts still cannot
        # skip drv.quit() -- a leaked session would block the next test.
        try:
            # rep_call is stashed by the pytest_runtest_makereport hook below.
            # Absent means the test never reached the call phase (setup error).
            if getattr(request.node, "rep_call", None) and request.node.rep_call.failed:
                _capture_failure_artifacts(drv, request.node.nodeid)
        finally:
            drv.quit()  # ends the session and releases the simulator


# Depending on `driver` binds the wait to this test's session and, as a side
# effect, guarantees the session exists before the test starts.
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
    # The `+tag` sub-address keeps a single mailbox while making each run unique;
    # 12 hex chars of a UUID4 is plenty of entropy to never repeat in practice.
    return f"stagetime.qa+{uuid.uuid4().hex[:12]}@stagetimepnw.test"


# --------------------------------------------------------------------------- #
# Failure artifacts                                                            #
# --------------------------------------------------------------------------- #
# Pytest calls this for each of the three phases of a test (setup / call /
# teardown). A fixture cannot otherwise see whether its test passed, so this
# hook copies each phase's report onto the test item where `driver` can read it.
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield          # let pytest build the report first
    rep = outcome.get_result()
    # Yields item.rep_setup / item.rep_call / item.rep_teardown.
    setattr(item, f"rep_{rep.when}", rep)


def _capture_failure_artifacts(drv, nodeid: str) -> None:
    """Save a screenshot and the UI hierarchy for a failed test, for debugging
    after the fact once the simulator state is gone."""
    out_dir = Path(_env("STAGETIME_ARTIFACTS_DIR", "artifacts"))
    out_dir.mkdir(parents=True, exist_ok=True)  # exist_ok => safe on later tests
    # A nodeid like "tests/test_signup.py::test_valid" contains "/" and ":",
    # so squash anything that is not word/dot/dash into "_" for a legal filename.
    stem = re.sub(r"[^\w.-]+", "_", nodeid)
    try:
        # The .png shows what was on screen; the .xml is the XCUITest element
        # tree, which is what you actually need to fix a broken locator.
        drv.save_screenshot(str(out_dir / f"{stem}.png"))
        (out_dir / f"{stem}.xml").write_text(drv.page_source, encoding="utf-8")
    except Exception as exc:  # never mask the real test failure
        # Broad catch on purpose: a dead session here must not replace the
        # assertion error the report is supposed to show.
        print(f"[artifacts] could not capture failure state: {exc!r}")
