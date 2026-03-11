import pytest
import requests

from guardian.core import plugins as core_plugins
from guardian.plugins.plugin_manifest import PluginManifest


def _manifest(plugin_id: str, cap_action: tuple[str, str]) -> PluginManifest:
    capability, action = cap_action
    return PluginManifest.model_validate(
        {
            "schema_version": "1.0",
            "id": plugin_id,
            "name": plugin_id,
            "version": "0.1.0",
            "base_url": "https://plugin.example",
            "capabilities": [{"id": capability, "actions": [action]}],
        }
    )


def test_invoke_capability_fails_on_zero_matches(monkeypatch):
    monkeypatch.setattr(core_plugins, "list_plugin_manifests", lambda: [])

    with pytest.raises(core_plugins.PluginFacadeError) as exc_info:
        core_plugins.invoke_capability("chat", "reply", input={})

    assert exc_info.value.code == "not_found"


def test_invoke_capability_fails_on_multiple_matches(monkeypatch):
    manifests = [
        _manifest("a", ("chat", "reply")),
        _manifest("b", ("chat", "reply")),
    ]
    monkeypatch.setattr(core_plugins, "list_plugin_manifests", lambda: manifests)

    with pytest.raises(core_plugins.PluginFacadeError) as exc_info:
        core_plugins.invoke_capability("chat", "reply", input={})

    assert exc_info.value.code == "ambiguous"


def test_explicit_plugin_invocation_works_when_multiple_share_operation(monkeypatch):
    manifests = [
        _manifest("a", ("chat", "reply")),
        _manifest("b", ("chat", "reply")),
    ]
    monkeypatch.setattr(core_plugins, "list_plugin_manifests", lambda: manifests)

    sent = {}

    class DummyResponse:
        def json(self):
            return {"ok": True, "output": {"message": "hello"}}

    def fake_post(url, json, timeout):
        sent["url"] = url
        sent["json"] = json
        sent["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr(core_plugins.requests, "post", fake_post)
    result = core_plugins.invoke_plugin(
        "a",
        "chat",
        "reply",
        input={"prompt": "hi"},
        context={"request_id": "req-1"},
    )

    assert result == {"ok": True, "output": {"message": "hello"}}
    assert sent["url"] == "https://plugin.example/invoke"
    assert sent["timeout"] == core_plugins.INVOKE_TIMEOUT_SECONDS
    assert sent["json"] == {
        "protocol_version": "1.0",
        "plugin_id": "a",
        "capability": "chat",
        "action": "reply",
        "input": {"prompt": "hi"},
        "context": {
            "request_id": "req-1",
            "thread_id": None,
            "user_id": None,
        },
    }


def test_invoke_plugin_normalizes_timeout(monkeypatch):
    monkeypatch.setattr(
        core_plugins,
        "list_plugin_manifests",
        lambda: [_manifest("a", ("chat", "reply"))],
    )

    def raise_timeout(*_args, **_kwargs):
        raise requests.Timeout("boom")

    monkeypatch.setattr(core_plugins.requests, "post", raise_timeout)

    with pytest.raises(core_plugins.PluginFacadeError) as exc_info:
        core_plugins.invoke_plugin("a", "chat", "reply", input={})

    assert exc_info.value.code == "timeout"


def test_invoke_plugin_normalizes_transport_failure(monkeypatch):
    monkeypatch.setattr(
        core_plugins,
        "list_plugin_manifests",
        lambda: [_manifest("a", ("chat", "reply"))],
    )

    def raise_transport(*_args, **_kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(core_plugins.requests, "post", raise_transport)

    with pytest.raises(core_plugins.PluginFacadeError) as exc_info:
        core_plugins.invoke_plugin("a", "chat", "reply", input={})

    assert exc_info.value.code == "transport_failure"


def test_invoke_plugin_normalizes_malformed_json(monkeypatch):
    monkeypatch.setattr(
        core_plugins,
        "list_plugin_manifests",
        lambda: [_manifest("a", ("chat", "reply"))],
    )

    class BadJsonResponse:
        def json(self):
            raise ValueError("invalid")

    monkeypatch.setattr(
        core_plugins.requests,
        "post",
        lambda *_args, **_kwargs: BadJsonResponse(),
    )

    with pytest.raises(core_plugins.PluginFacadeError) as exc_info:
        core_plugins.invoke_plugin("a", "chat", "reply", input={})

    assert exc_info.value.code == "invalid_response"


def test_invoke_plugin_normalizes_non_conforming_response(monkeypatch):
    monkeypatch.setattr(
        core_plugins,
        "list_plugin_manifests",
        lambda: [_manifest("a", ("chat", "reply"))],
    )

    class InvalidResponse:
        def json(self):
            return {"output": {"message": "missing ok"}}

    monkeypatch.setattr(
        core_plugins.requests,
        "post",
        lambda *_args, **_kwargs: InvalidResponse(),
    )

    with pytest.raises(core_plugins.PluginFacadeError) as exc_info:
        core_plugins.invoke_plugin("a", "chat", "reply", input={})

    assert exc_info.value.code == "invalid_response"
