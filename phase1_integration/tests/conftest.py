"""Test configuration for Phase 1 Integration tests."""

import pytest
import asyncio
import sys

# Add phase1_integration to path
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio as the async backend."""
    return "asyncio"
