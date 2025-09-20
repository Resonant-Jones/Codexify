import os
import socket

import pytest


def _internet():
    try:
        socket.create_connection(("1.1.1.1", 53), 1)
        return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _internet() or not os.getenv("ALLOW_NET_TESTS"),
    reason="Network tests are disabled by config or no internet.",
)


def pytest_collection_modifyitems(config, items):
    config.addinivalue_line(
        "markers", "skip(reason): mark test to be skipped with a reason"
    )
    if _internet() and os.getenv("ALLOW_NET_TESTS"):
        return
    skip = pytest.mark.skip(reason="network disabled")
    for item in items:
        if "export_notion" in str(item.fspath):
            item.add_marker(skip)
