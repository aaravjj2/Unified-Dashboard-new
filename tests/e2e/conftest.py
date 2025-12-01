"""
Playwright E2E Test Configuration

Configures pytest-playwright for headed browser testing.
"""

import pytest


def pytest_addoption(parser):
    """Add custom CLI options."""
    # NOTE: --headed is already defined by pytest-playwright, so we skip it
    # Only add custom options not defined by pytest-playwright
    try:
        parser.addoption(
            "--slow-mo",
            type=int,
            default=0,
            help="Slow down browser operations by specified ms"
        )
    except ValueError:
        # Option already exists
        pass


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig):
    """Configure browser launch arguments."""
    slow_mo = pytestconfig.getoption("--slow-mo", default=0)
    
    return {
        **browser_type_launch_args,
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
