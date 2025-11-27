"""
Playwright E2E Test Configuration

Configures pytest-playwright for headed browser testing.
"""

import pytest


def pytest_addoption(parser):
    """Add custom CLI options."""
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed (visible browser) mode"
    )
    parser.addoption(
        "--slow-mo",
        type=int,
        default=0,
        help="Slow down browser operations by specified ms"
    )


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig):
    """Configure browser launch arguments."""
    headed = pytestconfig.getoption("--headed")
    slow_mo = pytestconfig.getoption("--slow-mo")
    
    return {
        **browser_type_launch_args,
        "headless": not headed,  # HEADLESS=False when --headed flag is used
        "slow_mo": slow_mo,
    }


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }
