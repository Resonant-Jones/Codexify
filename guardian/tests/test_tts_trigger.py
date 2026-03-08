from __future__ import annotations

import requests

from guardian.audio import tts_trigger
from guardian.core import plugins as core_plugins
from guardian.plugins.plugin_manifest import PluginManifest


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, json_exc=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._json_exc = json_exc

    def json(self):
        if self._json_exc is not None:
            raise self._json_exc
        return self._payload


def _tts_manifest(
    plugin_id: str = "tts_service",
    *,
    base_url: str = "https://tts.example",
) -> PluginManifest:
    return PluginManifest(
        schema_version="1.0",
        id=plugin_id,
        name="TTS Service",
        version="1.0.0",
        base_url=base_url,
        capabilities=[{"id": "tts", "actions": ["speak"]}],
    )


def test_tts_routes_through_invoke_capability(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_invoke(capability, action, input, context=None):
        captured["capability"] = capability
        captured["action"] = action
        captured["input"] = input
        captured["context"] = context
        return {"output": {"status": "ok"}}

    monkeypatch.setattr(tts_trigger, "invoke_capability", _fake_invoke)

    result = tts_trigger.trigger_tts_if_available(
        "hello",
        metadata={"thread_id": "thread-1", "user_id": "user-1"},
    )

    assert result is True
    assert captured["capability"] == "tts"
    assert captured["action"] == "speak"
    assert captured["input"] == {
        "text": "hello",
        "metadata": {"thread_id": "thread-1", "user_id": "user-1"},
    }
    assert captured["context"] == {
        "request_id": None,
        "thread_id": "thread-1",
        "user_id": "user-1",
    }


def test_tts_uses_canonical_invoke_envelope(monkeypatch):
    manifest = _tts_manifest(base_url="https://voice.example")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    captured: dict[str, object] = {}

    def _fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse(payload={"output": {"spoken": True}})

    monkeypatch.setattr(core_plugins.requests, "post", _fake_post)

    result = tts_trigger.trigger_tts_if_available(
        "speak this",
        metadata={
            "request_id": "req-1",
            "thread_id": "thread-1",
            "user_id": "user-1",
        },
    )

    assert result is True
    assert captured["url"] == "https://voice.example/invoke"
    assert captured["timeout"] == core_plugins.INVOKE_TIMEOUT_SECONDS
    assert captured["headers"] == {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    assert captured["json"] == {
        "protocol_version": "1.0",
        "plugin_id": "tts_service",
        "capability": "tts",
        "action": "speak",
        "input": {
            "text": "speak this",
            "metadata": {
                "request_id": "req-1",
                "thread_id": "thread-1",
                "user_id": "user-1",
            },
        },
        "context": {
            "request_id": "req-1",
            "thread_id": "thread-1",
            "user_id": "user-1",
        },
    }


def test_tts_handles_canonical_facade_failures(monkeypatch):
    manifest = _tts_manifest()
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    outcomes = [
        ("timeout", lambda: (_ for _ in ()).throw(requests.Timeout("boom"))),
        (
            "transport_failure",
            lambda: (_ for _ in ()).throw(requests.ConnectionError("boom")),
        ),
        ("invalid_response", lambda: FakeResponse(json_exc=ValueError("bad"))),
        ("invalid_response", lambda: FakeResponse(payload={"result": "bad"})),
        (
            "remote_error",
            lambda: FakeResponse(
                payload={
                    "ok": False,
                    "output": None,
                    "error": {
                        "code": "synthesis_failed",
                        "message": "failed",
                        "retryable": False,
                    },
                }
            ),
        ),
        (
            "remote_error",
            lambda: FakeResponse(status_code=500, payload={"error": "x"}),
        ),
    ]

    for expected_code, factory in outcomes:
        calls = {"count": 0}

        def _fake_post(url, json, headers, timeout):
            calls["count"] += 1
            return factory()

        monkeypatch.setattr(core_plugins.requests, "post", _fake_post)
        warnings: list[str] = []
        monkeypatch.setattr(
            tts_trigger.logger,
            "warning",
            lambda msg, *args: warnings.append(msg % args if args else msg),
        )

        result = tts_trigger.trigger_tts_if_available("hello")

        assert result is False
        assert calls["count"] == 1
        assert any(f"code={expected_code}" in line for line in warnings)


def test_tts_fails_deterministically_on_absence_and_ambiguity(monkeypatch):
    manifests_by_mode = {
        "not_found": [],
        "ambiguous": [_tts_manifest("a"), _tts_manifest("b")],
    }

    for expected_code, manifests in manifests_by_mode.items():
        monkeypatch.setattr(
            core_plugins,
            "list_plugin_manifests",
            lambda manifests=manifests: manifests,
        )
        post_calls = {"count": 0}

        def _fake_post(url, json, headers, timeout):
            post_calls["count"] += 1
            return FakeResponse(payload={"output": {"spoken": True}})

        monkeypatch.setattr(core_plugins.requests, "post", _fake_post)
        warnings: list[str] = []
        monkeypatch.setattr(
            tts_trigger.logger,
            "warning",
            lambda msg, *args: warnings.append(msg % args if args else msg),
        )

        result = tts_trigger.trigger_tts_if_available("hello")

        assert result is False
        assert post_calls["count"] == 0
        assert any(f"code={expected_code}" in line for line in warnings)
