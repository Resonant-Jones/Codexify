from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from guardian.browser_host import http_adapter
from guardian.routes import browser_host


def _settings(*, dev: bool, negotiation: bool, attachment: bool) -> SimpleNamespace:
    return SimpleNamespace(
        GUARDIAN_DEV_MODE=dev,
        GUARDIAN_BROWSER_HOST_NEGOTIATION_DEV_ENABLED=negotiation,
        GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED=attachment,
    )


def _routes(app: FastAPI) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if route.path.startswith("/dev/browser-host/v1")
    }


@pytest.mark.parametrize(
    ("dev", "negotiation", "attachment", "exposure", "expected"),
    [
        (False, False, False, "local_safe", set()),
        (True, False, False, "local_safe", set()),
        (False, True, False, "local_safe", set()),
        (True, True, False, "public_allowlist", set()),
        (True, True, False, "local_safe", {("POST", "/dev/browser-host/v1/negotiate")}),
        (
            True,
            False,
            True,
            "local_safe",
            {
                ("POST", "/dev/browser-host/v1/attachment-grants"),
                ("POST", "/dev/browser-host/v1/attachments"),
            },
        ),
        (
            True,
            True,
            True,
            "local_safe",
            {
                ("POST", "/dev/browser-host/v1/negotiate"),
                ("POST", "/dev/browser-host/v1/attachment-grants"),
                ("POST", "/dev/browser-host/v1/attachments"),
            },
        ),
    ],
)
def test_negotiation_and_attachment_have_independent_three_gate_route_sets(
    monkeypatch: pytest.MonkeyPatch,
    dev: bool,
    negotiation: bool,
    attachment: bool,
    exposure: str,
    expected: set[tuple[str, str]],
) -> None:
    settings = _settings(dev=dev, negotiation=negotiation, attachment=attachment)
    monkeypatch.setattr(http_adapter, "get_settings", lambda: settings)
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: exposure)
    app = FastAPI()
    if attachment:
        http_adapter.install_browser_host_attachment_adapter(app, browser_host.router)
    if negotiation:
        http_adapter.install_browser_host_negotiation_adapter(
            app, browser_host.negotiation_router
        )
    assert _routes(app) == expected
    if negotiation and expected:
        assert getattr(app.state, http_adapter.NEGOTIATION_POLICY_STATE_KEY) is not None
    else:
        assert not hasattr(app.state, http_adapter.NEGOTIATION_POLICY_STATE_KEY)


def test_disabled_negotiation_does_not_create_policy_or_duplicate_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_adapter,
        "get_settings",
        lambda: _settings(dev=True, negotiation=True, attachment=False),
    )
    monkeypatch.setattr(http_adapter, "_exposure_mode", lambda: "local_safe")
    app = FastAPI()
    assert http_adapter.install_browser_host_negotiation_adapter(
        app, browser_host.negotiation_router
    )
    with pytest.raises(RuntimeError, match="already_installed"):
        http_adapter.install_browser_host_negotiation_adapter(
            app, browser_host.negotiation_router
        )
    assert len([route for route in app.routes if route.path.endswith("/negotiate")]) == 1
    assert http_adapter.shutdown_browser_host_negotiation_adapter(app) is True
    assert getattr(app.state, http_adapter.NEGOTIATION_POLICY_STATE_KEY) is None
