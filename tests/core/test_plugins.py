import requests

from guardian.core import plugins as core_plugins
from guardian.plugins.plugin_manifest import PluginManifest


class DummyRuntimeLoader:
    def __init__(self, plugins=None):
        self.plugins = plugins or {}
        self.load_calls = 0

    def load_all_plugins(self):
        self.load_calls += 1
        self.plugins["loaded"] = object()


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, json_exc=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._json_exc = json_exc

    def json(self):
        if self._json_exc is not None:
            raise self._json_exc
        return self._payload


def _manifest(
    plugin_id: str,
    *,
    base_url: str,
    operations: list[tuple[str, str]] | None = None,
) -> PluginManifest:
    operations = operations or [("tts", "speak")]
    grouped_actions: dict[str, list[str]] = {}
    for capability, action in operations:
        grouped_actions.setdefault(capability, []).append(action)
    return PluginManifest(
        schema_version="1.0",
        id=plugin_id,
        name=plugin_id,
        version="1.0.0",
        base_url=base_url,
        capabilities=[
            {"id": capability, "actions": actions}
            for capability, actions in grouped_actions.items()
        ],
    )


def test_load_runtime_plugins_loads_once_when_empty(monkeypatch):
    loader = DummyRuntimeLoader()
    monkeypatch.setattr(
        core_plugins, "get_runtime_plugin_loader", lambda: loader
    )

    loaded = core_plugins.load_runtime_plugins()

    assert loaded is loader
    assert loader.load_calls == 1


def test_load_runtime_plugins_skips_reload_when_registry_present(monkeypatch):
    loader = DummyRuntimeLoader(plugins={"existing": object()})
    monkeypatch.setattr(
        core_plugins, "get_runtime_plugin_loader", lambda: loader
    )

    loaded = core_plugins.load_runtime_plugins()

    assert loaded is loader
    assert loader.load_calls == 0


def test_get_plugin_manifest_by_capability_is_case_insensitive(monkeypatch):
    manifests = [
        _manifest(
            "non_tts",
            base_url="https://voice-a.example",
            operations=[("vision", "classify")],
        ),
        _manifest(
            "voice",
            base_url="https://voice-b.example",
            operations=[("TTS", "Speak"), ("audio", "mix")],
        ),
    ]
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: manifests
    )

    manifest = core_plugins.get_plugin_manifest_by_capability("tts")

    assert manifest is not None
    assert manifest.id == "voice"
    assert core_plugins.get_plugin_manifest_by_capability("missing") is None


def test_find_plugins_by_capability_action_returns_matching_plugins(
    monkeypatch,
):
    manifests = [
        _manifest("voice_a", base_url="https://voice-a.example"),
        _manifest("voice_b", base_url="https://voice-b.example"),
        _manifest(
            "vision",
            base_url="https://vision.example",
            operations=[("vision", "classify")],
        ),
    ]
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: manifests
    )

    matches = core_plugins.find_plugins_by_capability_action("tts", "speak")

    assert [manifest.id for manifest in matches] == ["voice_a", "voice_b"]


def test_invoke_plugin_sends_canonical_envelope(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    captured: dict[str, object] = {}

    def _fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse(payload={"output": {"status": "ok"}})

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    payload = core_plugins.invoke_plugin(
        "voice",
        capability="tts",
        action="speak",
        input={"text": "hello"},
        context={
            "request_id": "req-123",
            "thread_id": None,
            "user_id": None,
            "api_key": "should_not_forward",
        },
    )

    assert payload == {"output": {"status": "ok"}}
    assert captured["url"] == "https://voice.example/invoke"
    assert captured["timeout"] == core_plugins.INVOKE_TIMEOUT_SECONDS
    assert captured["headers"] == {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    assert "Authorization" not in captured["headers"]
    assert captured["json"] == {
        "protocol_version": "1.0",
        "plugin_id": "voice",
        "capability": "tts",
        "action": "speak",
        "input": {"text": "hello"},
        "context": {
            "request_id": "req-123",
            "thread_id": None,
            "user_id": None,
        },
    }


def test_invoke_capability_fails_on_zero_matches(monkeypatch):
    monkeypatch.setattr(core_plugins, "list_plugin_manifests", lambda: [])

    try:
        core_plugins.invoke_capability("tts", "speak", input={"text": "hello"})
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_NOT_FOUND


def test_invoke_capability_fails_on_multiple_matches(monkeypatch):
    manifests = [
        _manifest("voice_a", base_url="https://voice-a.example"),
        _manifest("voice_b", base_url="https://voice-b.example"),
    ]
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: manifests
    )

    try:
        core_plugins.invoke_capability("tts", "speak", input={"text": "hello"})
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_AMBIGUOUS
        assert exc.details == ["voice_a", "voice_b"]


def test_explicit_plugin_invocation_works_with_shared_operation(monkeypatch):
    manifests = [
        _manifest("voice_a", base_url="https://voice-a.example"),
        _manifest("voice_b", base_url="https://voice-b.example"),
    ]
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: manifests
    )
    captured: dict[str, object] = {}

    def _fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["plugin_id"] = json["plugin_id"]
        return FakeResponse(payload={"output": {"plugin": json["plugin_id"]}})

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    payload = core_plugins.invoke_plugin(
        "voice_b",
        capability="tts",
        action="speak",
        input={"text": "hello"},
    )

    assert payload == {"output": {"plugin": "voice_b"}}
    assert captured["plugin_id"] == "voice_b"
    assert captured["url"] == "https://voice-b.example/invoke"


def test_invoke_plugin_normalizes_timeout(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _fake_post(url, json, headers, timeout):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    try:
        core_plugins.invoke_plugin(
            "voice", "tts", "speak", input={"text": "hello"}
        )
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_TIMEOUT


def test_invoke_plugin_normalizes_connection_failure(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _fake_post(url, json, headers, timeout):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    try:
        core_plugins.invoke_plugin(
            "voice", "tts", "speak", input={"text": "hello"}
        )
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_TRANSPORT_FAILURE


def test_invoke_plugin_normalizes_malformed_json_response(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _fake_post(url, json, headers, timeout):
        return FakeResponse(status_code=200, json_exc=ValueError("bad json"))

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    try:
        core_plugins.invoke_plugin(
            "voice", "tts", "speak", input={"text": "hello"}
        )
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_INVALID_RESPONSE


def test_invoke_plugin_normalizes_nonconforming_response(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _fake_post(url, json, headers, timeout):
        return FakeResponse(
            status_code=200, payload={"result": "missing-output"}
        )

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    try:
        core_plugins.invoke_plugin(
            "voice", "tts", "speak", input={"text": "hello"}
        )
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_INVALID_RESPONSE


def test_invoke_plugin_rejects_non_object_output(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _fake_post(url, json, headers, timeout):
        return FakeResponse(
            status_code=200, payload={"output": "not-an-object"}
        )

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    try:
        core_plugins.invoke_plugin(
            "voice", "tts", "speak", input={"text": "hello"}
        )
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_INVALID_RESPONSE


def test_invoke_plugin_rejects_failed_ok_without_error_payload(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _fake_post(url, json, headers, timeout):
        return FakeResponse(
            status_code=200, payload={"ok": False, "output": {}}
        )

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    try:
        core_plugins.invoke_plugin(
            "voice", "tts", "speak", input={"text": "hello"}
        )
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_INVALID_RESPONSE


def test_invoke_plugin_normalizes_remote_error_response(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _fake_post(url, json, headers, timeout):
        return FakeResponse(
            status_code=500,
            payload={"error": {"code": "upstream_failure"}},
        )

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    try:
        core_plugins.invoke_plugin(
            "voice", "tts", "speak", input={"text": "hello"}
        )
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_REMOTE_ERROR


def test_unhealthy_plugin_still_appears_installed(monkeypatch):
    manifest = _manifest("voice", base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "_load_manifest_plugins", lambda: [manifest]
    )

    def _fake_get(url, timeout):
        raise requests.Timeout("health timeout")

    monkeypatch.setattr(core_plugins.requests, "get", _fake_get)

    manifests = core_plugins.list_plugin_manifests()

    assert [m.id for m in manifests] == ["voice"]
    try:
        core_plugins.get_plugin_health("voice")
        raise AssertionError("expected PluginFacadeError")
    except core_plugins.PluginFacadeError as exc:
        assert exc.code == core_plugins.ERROR_TIMEOUT
