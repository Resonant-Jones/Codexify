import os, socket, pytest

def _internet():
    try:
        socket.create_connection(("1.1.1.1", 53), 1)
        return True
    except OSError:
        return False

def pytest_collection_modifyitems(config, items):
    # Run network tests only if we have internet *and* the flag is set
    if _internet() and os.getenv("ALLOW_NET_TESTS"):
        return
    skip = pytest.mark.skip(reason="network disabled")
    for item in items:
        if "export_notion" in str(item.fspath):
            item.add_marker(skip)
