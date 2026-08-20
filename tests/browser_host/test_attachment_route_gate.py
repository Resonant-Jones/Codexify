from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from guardian.browser_host import http_adapter
from guardian.routes import browser_host


def _settings(*, dev_mode: bool, adapter_enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        GUARDIAN_DEV_MODE=dev_mode,
        GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED=adapter_enabled,
    )


def _route_paths(app: FastAPI) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/dev/browser-host/v1")
        for method in operations
    }


@pytest.mark.parametrize(
    ("dev_mode", "adapter_enabled", "exposure_mode"),
    [
        (False, False, "local_safe"),
        (True, False, "local_safe"),
        (False, True, "local_safe"),
        (True, True, "public_allowlist"),
    ],
)
def test_route_gate_keeps_adapter_absent_unless_all_conditions_hold(
    monkeypatch: pytest.MonkeyPatch,
    dev_mode: bool,
    adapter_enabled: bool,
    exposure_mode: str,
) -> None:
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: _settings(
            dev_mode=dev_mode,
            adapter_enabled=adapter_enabled,
        ),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: exposure_mode)

    app = FastAPI()
    mounted = http_adapter.install_browser_host_attachment_adapter(
        app, browser_host.router
    )

    assert mounted is False
    assert _route_paths(app) == set()
    assert not hasattr(app.state, http_adapter.STORE_STATE_KEY)


def test_enabled_gate_mounts_exactly_two_routes_and_one_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: _settings(dev_mode=True, adapter_enabled=True),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: "local_safe")

    app = FastAPI()
    assert http_adapter.install_browser_host_attachment_adapter(
        app, browser_host.router
    ) is True
    assert _route_paths(app) == {
        ("POST", "/dev/browser-host/v1/attachment-grants"),
        ("POST", "/dev/browser-host/v1/attachments"),
    }
    assert hasattr(app.state, http_adapter.STORE_STATE_KEY)
    assert http_adapter.browser_host_attachment_adapter_enabled() is True

    with pytest.raises(RuntimeError, match="already_installed"):
        http_adapter.install_browser_host_attachment_adapter(app, browser_host.router)


def test_shutdown_clears_application_store_and_releases_grants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: _settings(dev_mode=True, adapter_enabled=True),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: "local_safe")

    app = FastAPI()
    http_adapter.install_browser_host_attachment_adapter(app, browser_host.router)
    store = getattr(app.state, http_adapter.STORE_STATE_KEY)
    assert store.snapshot_for_testing() == ()

    assert http_adapter.shutdown_browser_host_attachment_adapter(app) is True
    assert getattr(app.state, http_adapter.STORE_STATE_KEY) is None
    assert getattr(app.state, http_adapter.ADAPTER_STATE_KEY) is False


def test_restart_does_not_reuse_old_application_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: _settings(dev_mode=True, adapter_enabled=True),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: "local_safe")

    first = FastAPI()
    second = FastAPI()
    http_adapter.install_browser_host_attachment_adapter(first, browser_host.router)
    http_adapter.install_browser_host_attachment_adapter(second, browser_host.router)
    assert getattr(first.state, http_adapter.STORE_STATE_KEY) is not getattr(
        second.state, http_adapter.STORE_STATE_KEY
    )
