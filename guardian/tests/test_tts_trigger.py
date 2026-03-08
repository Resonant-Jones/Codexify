from __future__ import annotations

import base64
import subprocess
from pathlib import Path

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


def _success_payload() -> dict[str, dict[str, str]]:
    return {
        "output": {
            "format": "wav",
            "mime_type": "audio/wav",
            "audio_base64": base64.b64encode(b"RIFF....WAVE").decode("ascii"),
        }
    }


def _patch_successful_playback(monkeypatch, command_id: str = "ffplay"):
    monkeypatch.setattr(
        tts_trigger,
        "_select_playback_command",
        lambda audio_path: tts_trigger.PlaybackCommandSelection(
            command_id=command_id,
            argv=[f"/usr/bin/{command_id}", audio_path],
            binary_path=f"/usr/bin/{command_id}",
        ),
    )
    monkeypatch.setattr(
        tts_trigger.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="", stderr=""
        ),
    )


def _patch_host_runtime(monkeypatch):
    monkeypatch.setattr(
        tts_trigger,
        "_detect_containerized_runtime",
        lambda: (False, None),
    )


def test_tts_routes_through_invoke_plugin(monkeypatch):
    manifest = _tts_manifest(plugin_id="chatterbox", base_url="http://tts:8000")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    _patch_host_runtime(monkeypatch)
    captured: dict[str, object] = {}

    def _fake_invoke(manifest, input_payload, context):
        captured["plugin_id"] = manifest.id
        captured["base_url"] = manifest.base_url
        captured["input"] = input_payload
        captured["context"] = context
        return _success_payload()

    monkeypatch.setattr(tts_trigger, "_invoke_tts_plugin", _fake_invoke)
    _patch_successful_playback(monkeypatch)

    result = tts_trigger.trigger_tts_with_result(
        "hello",
        metadata={"thread_id": "thread-1", "user_id": "user-1"},
    )

    assert result.ok is True
    assert captured["plugin_id"] == "chatterbox"
    assert captured["base_url"] == "http://tts:8000"
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
    _patch_host_runtime(monkeypatch)
    captured: dict[str, object] = {}

    def _fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse(payload=_success_payload())

    monkeypatch.setattr(tts_trigger.requests, "post", _fake_post)
    _patch_successful_playback(monkeypatch)

    result = tts_trigger.trigger_tts_with_result(
        "speak this",
        metadata={
            "request_id": "req-1",
            "thread_id": "thread-1",
            "user_id": "user-1",
        },
    )

    assert result.ok is True
    assert result.plugin_id == "tts_service"
    assert result.base_url == "https://voice.example"
    assert result.playback_command == "ffplay"
    assert result.output_keys == ["audio_base64", "format", "mime_type"]
    assert captured["url"] == "https://voice.example/invoke"
    assert captured["timeout"] == tts_trigger._tts_invoke_timeout_seconds()
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


def test_tts_handles_runtime_plugin_failures(monkeypatch):
    manifest = _tts_manifest()
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    _patch_host_runtime(monkeypatch)
    outcomes = [
        (
            "plugin_timeout",
            lambda: (_ for _ in ()).throw(requests.Timeout("boom")),
        ),
        (
            "plugin_unreachable",
            lambda: (_ for _ in ()).throw(requests.ConnectionError("boom")),
        ),
        ("invalid_payload", lambda: FakeResponse(json_exc=ValueError("bad"))),
        ("invalid_payload", lambda: FakeResponse(payload={"result": "bad"})),
        (
            "plugin_remote_error",
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
    ]

    for expected_failure, factory in outcomes:
        monkeypatch.setattr(
            tts_trigger.requests,
            "post",
            lambda url, json, headers, timeout, factory=factory: factory(),
        )
        warnings: list[str] = []
        monkeypatch.setattr(
            tts_trigger.logger,
            "warning",
            lambda msg, *args: warnings.append(msg % args if args else msg),
        )

        result = tts_trigger.trigger_tts_with_result("hello")

        assert result.ok is False
        assert result.failure_kind == expected_failure
        assert result.plugin_id == "tts_service"
        assert result.base_url == "https://tts.example"
        assert any("plugin_id=tts_service" in line for line in warnings)
        assert any("base_url=https://tts.example" in line for line in warnings)
        assert any(
            f"failure_kind={expected_failure}" in line for line in warnings
        )


def test_tts_fails_deterministically_on_absence_and_ambiguity(monkeypatch):
    manifests_by_mode = {
        "plugin_manifest_not_found": [],
        "plugin_selection_ambiguous": [_tts_manifest("a"), _tts_manifest("b")],
    }

    for expected_failure, manifests in manifests_by_mode.items():
        monkeypatch.setattr(
            core_plugins,
            "list_plugin_manifests",
            lambda manifests=manifests: manifests,
        )

        result = tts_trigger.trigger_tts_with_result("hello")

        assert result.ok is False
        assert result.failure_kind == expected_failure
        assert result.error_code in {"not_found", "ambiguous"}


def test_tts_fails_clearly_when_no_playback_binary_is_available(monkeypatch):
    manifest = _tts_manifest(base_url="http://tts:8000")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    _patch_host_runtime(monkeypatch)
    monkeypatch.setattr(
        tts_trigger,
        "_invoke_tts_plugin",
        lambda *args, **kwargs: _success_payload(),
    )
    monkeypatch.setattr(tts_trigger.shutil, "which", lambda name: None)
    warnings: list[str] = []
    monkeypatch.setattr(
        tts_trigger.logger,
        "warning",
        lambda msg, *args: warnings.append(msg % args if args else msg),
    )

    result = tts_trigger.trigger_tts_with_result("hello")

    assert result.ok is False
    assert result.failure_kind == "no_playback_binary_available"
    assert result.playback_command == "none"
    assert result.audio_source == "audio_base64"
    assert any("playback_command=none" in line for line in warnings)
    assert any("audio_source=audio_base64" in line for line in warnings)
    assert any("trail=manifest_discovery:ok" in line for line in warnings)


def test_tts_reports_playback_subprocess_nonzero_exit(monkeypatch):
    manifest = _tts_manifest(base_url="http://tts:8000")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    _patch_host_runtime(monkeypatch)
    monkeypatch.setattr(
        tts_trigger,
        "_invoke_tts_plugin",
        lambda *args, **kwargs: _success_payload(),
    )
    monkeypatch.setattr(
        tts_trigger.shutil,
        "which",
        lambda name: "/usr/bin/ffplay" if name == "ffplay" else None,
    )
    monkeypatch.setattr(
        tts_trigger.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            2,
            stdout="decoder stalled",
            stderr="generic playback error",
        ),
    )

    result = tts_trigger.trigger_tts_with_result("hello")

    assert result.ok is False
    assert result.failure_kind == "playback_subprocess_failed"
    assert result.playback_attempted is True
    assert result.playback_command == "ffplay"
    assert result.playback_return_code == 2
    assert result.stdout_summary == "decoder stalled"
    assert result.stderr_summary == "generic playback error"


def test_tts_distinguishes_local_audio_device_failures(monkeypatch):
    manifest = _tts_manifest(base_url="http://tts:8000")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    _patch_host_runtime(monkeypatch)
    monkeypatch.setattr(
        tts_trigger,
        "_invoke_tts_plugin",
        lambda *args, **kwargs: _success_payload(),
    )
    monkeypatch.setattr(
        tts_trigger.shutil,
        "which",
        lambda name: "/usr/bin/ffplay" if name == "ffplay" else None,
    )
    monkeypatch.setattr(
        tts_trigger.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            1,
            stdout="",
            stderr="ALSA lib pcm.c:2666 cannot open audio device",
        ),
    )

    result = tts_trigger.trigger_tts_with_result("hello")

    assert result.ok is False
    assert result.failure_kind == "local_audio_device_output_failure"


def test_tts_preserves_audio_artifact_and_warns_for_container_local_playback(
    monkeypatch, tmp_path
):
    manifest = _tts_manifest(base_url="http://tts:8000")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    monkeypatch.setattr(
        tts_trigger,
        "_invoke_tts_plugin",
        lambda *args, **kwargs: _success_payload(),
    )
    monkeypatch.setattr(
        tts_trigger,
        "_detect_containerized_runtime",
        lambda: (True, "/.dockerenv"),
    )
    monkeypatch.setattr(
        tts_trigger,
        "_host_inspectable_artifact_dir",
        lambda containerized: Path(tmp_path),
    )
    monkeypatch.setattr(
        tts_trigger.shutil,
        "which",
        lambda name: "/usr/bin/ffplay" if name == "ffplay" else None,
    )

    result = tts_trigger.trigger_tts_with_result(
        "hello",
        metadata={"request_id": "containerized-1"},
    )

    assert result.ok is False
    assert result.failure_kind == "container_local_playback_not_host_audible"
    assert result.audio_source == "audio_base64"
    assert result.output_keys == ["audio_base64", "format", "mime_type"]
    assert result.containerized is True
    assert result.containerization_reason == "/.dockerenv"
    assert result.host_audible_playback_plausible is False
    assert result.playback_attempted is False
    assert result.playback_command == "ffplay"
    assert result.playback_command_path == "/usr/bin/ffplay"
    assert result.artifact_path is not None
    assert result.artifact_bytes == len(b"RIFF....WAVE")
    assert Path(result.artifact_path).exists()
    assert Path(result.artifact_path).stat().st_size == len(b"RIFF....WAVE")


def test_tts_reports_origin_mismatch_or_unreachable_service(monkeypatch):
    manifest = _tts_manifest(
        plugin_id="chatterbox",
        base_url="http://localhost:8000",
    )
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )

    def _raise_transport(*args, **kwargs):
        raise core_plugins.PluginFacadeError(
            code=core_plugins.ERROR_TRANSPORT_FAILURE,
            message="Plugin transport failure",
            plugin_id="chatterbox",
            capability="tts",
            action="speak",
        )

    monkeypatch.setattr(tts_trigger, "_invoke_tts_plugin", _raise_transport)

    result = tts_trigger.trigger_tts_with_result("hello")

    assert result.ok is False
    assert result.failure_kind == "plugin_unreachable"
    assert result.base_url == "http://localhost:8000"


def test_tts_malformed_success_output_fails_clearly(monkeypatch):
    manifest = _tts_manifest(base_url="http://tts:8000")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    _patch_host_runtime(monkeypatch)
    monkeypatch.setattr(
        tts_trigger,
        "_invoke_tts_plugin",
        lambda *args, **kwargs: {"output": {"format": "wav"}},
    )

    result = tts_trigger.trigger_tts_with_result("hello")

    assert result.ok is False
    assert result.failure_kind == "invalid_payload"
    assert result.failure_stage == "audio_materialization"
    assert result.error_code == "missing_audio_payload"


def test_tts_runtime_self_check_reports_expected_dependency_state(monkeypatch):
    manifest = _tts_manifest(plugin_id="chatterbox", base_url="http://tts:8000")
    monkeypatch.setattr(
        core_plugins, "list_plugin_manifests", lambda: [manifest]
    )
    monkeypatch.setattr(
        tts_trigger,
        "_detect_containerized_runtime",
        lambda: (True, "/.dockerenv"),
    )
    monkeypatch.setattr(
        core_plugins,
        "get_plugin_health",
        lambda plugin_id: {
            "status": "healthy",
            "default_provider": "qwen3_1.7b",
        },
    )
    monkeypatch.setattr(
        tts_trigger.shutil,
        "which",
        lambda name: "/usr/bin/ffplay" if name == "ffplay" else None,
    )

    report = tts_trigger.get_tts_runtime_self_check()

    assert report["manifest_discoverable"] is True
    assert report["selected_plugin_id"] == "chatterbox"
    assert report["selected_plugin_base_url"] == "http://tts:8000"
    assert report["selected_provider"] == "qwen3_1.7b"
    assert report["runtime"]["containerized"] is True
    assert report["runtime"]["containerization_reason"] == "/.dockerenv"
    assert report["plugin_health"]["reachable"] is True
    assert report["plugin_health"]["url"] == "http://tts:8000/health"
    assert report["playback"]["binary_path"] == "/usr/bin/ffplay"
    assert report["playback"]["command"] == "ffplay"
    assert report["playback"]["host_audible_playback_plausible"] is False
