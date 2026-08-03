"""Local conftest for browser_host_harness tests.

These tests are dependency-free and must not import guardian modules.
Overrides the root conftest's guardian-importing autouse fixture.
"""

import os
import pytest

# Ensure we don't trigger guardian imports
os.environ.setdefault("CODEXIFY_DISABLE_DOTENV", "1")
os.environ.setdefault("GUARDIAN_API_KEY", "test-api-key")


@pytest.fixture(autouse=True)
def _drain_chat_import_queue():
    """No-op override of the root conftest fixture that imports guardian."""
    yield
