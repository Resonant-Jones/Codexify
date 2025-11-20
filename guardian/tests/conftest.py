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


# --- Patched TestClient fixture for guardian tests -------------------------
from fastapi.testclient import TestClient as _BaseTestClient
from guardian.guardian_api import app as _app


class _PatchedTestClient(_BaseTestClient):
    """TestClient subclass that accepts json=/stream= for GET requests.

    Some tests pass httpx-style keyword arguments that FastAPI's TestClient
    does not support directly. This wrapper normalises those into a generic
    request() call so the tests can exercise the API as intended.
    """

    def get(self, url: str, *args, **kwargs):
        # Normalise unexpected kwargs used in tests
        _ = kwargs.pop("stream", None)
        json_payload = kwargs.pop("json", None)
        if json_payload is not None:
            resp = self.request("GET", url, json=json_payload, *args, **kwargs)
        else:
            resp = super().get(url, *args, **kwargs)

        # Patch Response.iter_lines to ignore httpx-style kwargs like chunk_size
        orig_iter_lines = getattr(resp, "iter_lines", None)
        if callable(orig_iter_lines):

            def _patched_iter_lines(*i_args, **i_kwargs):
                # Drop httpx-style kwargs that Starlette's Response.iter_lines
                # does not accept.
                i_kwargs.pop("chunk_size", None)
                i_kwargs.pop("decode_unicode", None)
                return orig_iter_lines(*i_args, **i_kwargs)

            resp.iter_lines = _patched_iter_lines  # type: ignore[assignment]

        return resp


@pytest.fixture
def client() -> _PatchedTestClient:
    """Patched TestClient fixture used by guardian/tests."""
    return _PatchedTestClient(_app)
