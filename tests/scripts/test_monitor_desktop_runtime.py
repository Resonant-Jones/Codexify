from __future__ import annotations

import json
from pathlib import Path

import requests

from scripts.ops import monitor_desktop_runtime as monitor


def test_monitor_sends_operator_key_only_to_retrieval_without_redirects(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "monitor-operator-key")
    calls = []

    def fetch(url, timeout, **kwargs):
        calls.append((url, kwargs))
        return _healthy_fetch(url, timeout)

    result = monitor._probe_runtime(
        base_url="http://127.0.0.1:8888", timeout=2, request_get=fetch
    )
    assert result["status"] == monitor.STATUS_READY
    for url, options in calls:
        if url.endswith("/api/health/retrieval"):
            assert options == {
                "headers": {"X-API-Key": "monitor-operator-key"},
                "allow_redirects": False,
            }
        else:
            assert options == {}
    assert "monitor-operator-key" not in json.dumps(result)


def test_monitor_without_operator_key_reports_retrieval_not_ready(monkeypatch):
    monkeypatch.delenv("GUARDIAN_API_KEY", raising=False)

    def fetch(url, timeout, **kwargs):
        assert kwargs == {}
        if url.endswith("/api/health/retrieval"):
            return _Response({"detail": "Operator authentication required"}, 401)
        return _healthy_fetch(url, timeout)

    result = monitor._probe_runtime(
        base_url="http://127.0.0.1:8888", timeout=2, request_get=fetch
    )
    assert result["status"] == monitor.STATUS_NOT_READY


def test_monitor_redacts_credentials_from_request_preparation_errors(monkeypatch):
    secret = "synthetic-operator-secret\ninvalid-header"
    monkeypatch.setenv("GUARDIAN_API_KEY", secret)

    def fetch(url, timeout, **kwargs):
        if kwargs.get("headers"):
            # Exercise Requests' real header validator without sending traffic.
            requests.Request("GET", url, headers=kwargs["headers"]).prepare()
        return _healthy_fetch(url, timeout)

    result = monitor._probe_runtime(
        base_url="http://127.0.0.1:8888", timeout=2, request_get=fetch
    )
    serialized = json.dumps(result)
    assert "InvalidHeader" in serialized
    assert "credentialed request failed" in serialized
    assert "synthetic-operator-secret" not in serialized
    assert "invalid-header" not in serialized


class _Response:
    def __init__(
        self, payload: dict[str, object], status_code: int = 200
    ) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, object]:
        return self._payload


def _healthy_fetch(url: str, timeout: float, **_kwargs):
    _ = timeout
    if url.endswith("/health"):
        return _Response(
            {"status": "healthy", "details": {"supported_profile": {}}}
        )
    if url.endswith("/health/chat"):
        return _Response({"status": "healthy", "notes": ["queue empty"]})
    if url.endswith("/api/health/llm"):
        return _Response(
            {
                "status": "healthy",
                "provider": "local",
                "model": "qwen3.5:0.8b",
                "provider_runtime": {"enabled": True},
            }
        )
    if url.endswith("/api/health/retrieval"):
        return _Response(
            {
                "status": "ready",
                "ok": True,
                "proof_capable": True,
                "same_runtime_as_worker": True,
            }
        )
    if url.endswith("/api/llm/catalog?include=all"):
        return _Response(
            {
                "providers": [
                    {
                        "id": "local",
                        "enabled": True,
                        "available": True,
                        "truth": {
                            "configured": True,
                            "authorized": True,
                            "discoverable": True,
                            "selectable": True,
                        },
                    }
                ]
            }
        )
    raise AssertionError(f"unexpected url: {url}")


def _degraded_provider_fetch(url: str, timeout: float, **_kwargs):
    _ = timeout
    if url.endswith("/health"):
        return _Response({"status": "healthy", "details": {}})
    if url.endswith("/health/chat"):
        return _Response({"status": "healthy"})
    if url.endswith("/api/health/llm"):
        return _Response(
            {
                "status": "degraded",
                "provider": "local",
                "provider_runtime": {"enabled": True},
            }
        )
    if url.endswith("/api/health/retrieval"):
        return _Response(
            {
                "status": "ready",
                "ok": True,
                "proof_capable": True,
                "same_runtime_as_worker": True,
            }
        )
    if url.endswith("/api/llm/catalog?include=all"):
        return _Response(
            {
                "providers": [
                    {
                        "id": "local",
                        "enabled": True,
                        "available": True,
                        "truth": {
                            "configured": True,
                            "authorized": True,
                            "discoverable": True,
                            "selectable": True,
                        },
                    }
                ]
            }
        )
    raise AssertionError(f"unexpected url: {url}")


def _unreachable_runtime_fetch(url: str, timeout: float, **_kwargs):
    _ = timeout
    if url.endswith("/health"):
        raise requests.exceptions.ConnectionError("backend unreachable")
    if url.endswith("/health/chat"):
        return _Response({"status": "healthy"})
    if url.endswith("/api/health/llm"):
        return _Response({"status": "healthy"})
    if url.endswith("/api/health/retrieval"):
        return _Response(
            {
                "status": "ready",
                "ok": True,
                "proof_capable": True,
                "same_runtime_as_worker": True,
            }
        )
    if url.endswith("/api/llm/catalog?include=all"):
        return _Response(
            {
                "providers": [
                    {
                        "id": "local",
                        "enabled": True,
                        "available": True,
                        "truth": {
                            "configured": True,
                            "authorized": True,
                            "discoverable": True,
                            "selectable": True,
                        },
                    }
                ]
            }
        )
    raise AssertionError(f"unexpected url: {url}")


def _write_startup_state(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "setupComplete": True,
                "runtimeProfile": "packaged",
                "envPath": "/tmp/runtime/.env",
                "handoffTarget": "http://127.0.0.1:8888",
                "detail": "startup ready",
            }
        ),
        encoding="utf-8",
    )


def _write_packaged_runtime(runtime_root: Path) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / ".codexify-packaged-runtime").write_text(
        "", encoding="utf-8"
    )
    (runtime_root / ".codexify-runtime-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "app_version": "0.1.0",
                "runtime_context": "packaged",
                "packaged": True,
                "runtime_home": str(runtime_root),
                "compose_file": str(runtime_root / "docker-compose.yml"),
                "env_file": str(runtime_root / ".env"),
                "env_template": str(runtime_root / ".env.template"),
                "env_example": str(runtime_root / ".env.example"),
                "resource_root": str(runtime_root / "resources"),
                "marker_file": str(runtime_root / ".codexify-packaged-runtime"),
                "attachment_state": "first-run",
                "bundled_assets": ["docker-compose.yml"],
                "placeholder_directories": ["backend"],
            }
        ),
        encoding="utf-8",
    )


def test_monitor_reports_ready_runtime_and_launcher_artifacts(tmp_path):
    app_support_root = tmp_path / "Application Support" / "Codexify"
    runtime_root = tmp_path / "Codexify"
    app_support_root.mkdir(parents=True, exist_ok=True)
    _write_startup_state(
        app_support_root / ".codexify-launcher-startup-state.json"
    )
    _write_packaged_runtime(runtime_root)

    snapshot = monitor.collect_monitor_snapshot(
        base_url="http://127.0.0.1:8888",
        app_support_root=app_support_root,
        runtime_root=runtime_root,
        request_get=_healthy_fetch,
    )

    assert snapshot["overall_status"] == monitor.STATUS_READY
    assert snapshot["runtime"]["status"] == monitor.STATUS_READY
    assert snapshot["provider"]["status"] == monitor.STATUS_READY
    assert snapshot["launcher"]["status"] == monitor.STATUS_READY
    assert (
        snapshot["launcher"]["startup_state"]["status"] == monitor.STATUS_READY
    )
    assert (
        snapshot["launcher"]["packaged_runtime"]["status"]
        == monitor.STATUS_READY
    )
    assert snapshot["next_actions"] == []


def test_monitor_reports_missing_launcher_artifacts_as_missing_artifact(
    tmp_path,
):
    app_support_root = tmp_path / "Application Support" / "Codexify"
    runtime_root = tmp_path / "Codexify"
    app_support_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)

    snapshot = monitor.collect_monitor_snapshot(
        base_url="http://127.0.0.1:8888",
        app_support_root=app_support_root,
        runtime_root=runtime_root,
        request_get=_healthy_fetch,
    )

    assert snapshot["runtime"]["status"] == monitor.STATUS_READY
    assert (
        snapshot["launcher"]["startup_state"]["status"]
        == monitor.STATUS_MISSING_ARTIFACT
    )
    assert (
        snapshot["launcher"]["packaged_runtime"]["status"]
        == monitor.STATUS_MISSING_ARTIFACT
    )
    assert snapshot["overall_status"] == monitor.STATUS_MISSING_ARTIFACT
    assert any(
        "startup-state file" in action.lower()
        for action in snapshot["next_actions"]
    )


def test_monitor_reports_unreachable_runtime_surface(tmp_path):
    app_support_root = tmp_path / "Application Support" / "Codexify"
    runtime_root = tmp_path / "Codexify"
    app_support_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)

    snapshot = monitor.collect_monitor_snapshot(
        base_url="http://127.0.0.1:8888",
        app_support_root=app_support_root,
        runtime_root=runtime_root,
        request_get=_unreachable_runtime_fetch,
    )

    assert snapshot["runtime"]["reachability"] == "unreachable"
    assert (
        snapshot["runtime"]["surfaces"]["core"]["status"]
        == monitor.STATUS_UNREACHABLE
    )
    assert snapshot["overall_status"] == monitor.STATUS_UNREACHABLE


def test_monitor_reports_degraded_provider_surface(tmp_path):
    app_support_root = tmp_path / "Application Support" / "Codexify"
    runtime_root = tmp_path / "Codexify"
    app_support_root.mkdir(parents=True, exist_ok=True)
    _write_startup_state(
        app_support_root / ".codexify-launcher-startup-state.json"
    )
    _write_packaged_runtime(runtime_root)

    snapshot = monitor.collect_monitor_snapshot(
        base_url="http://127.0.0.1:8888",
        app_support_root=app_support_root,
        runtime_root=runtime_root,
        request_get=_degraded_provider_fetch,
    )

    assert snapshot["runtime"]["status"] == monitor.STATUS_READY
    assert snapshot["provider"]["status"] == monitor.STATUS_DEGRADED
    assert (
        snapshot["provider"]["surfaces"]["llm"]["status"]
        == monitor.STATUS_DEGRADED
    )
    assert snapshot["overall_status"] == monitor.STATUS_DEGRADED


def test_monitor_json_output_contract(tmp_path):
    app_support_root = tmp_path / "Application Support" / "Codexify"
    runtime_root = tmp_path / "Codexify"
    app_support_root.mkdir(parents=True, exist_ok=True)
    _write_startup_state(
        app_support_root / ".codexify-launcher-startup-state.json"
    )
    _write_packaged_runtime(runtime_root)

    snapshot = monitor.collect_monitor_snapshot(
        base_url="http://127.0.0.1:8888",
        app_support_root=app_support_root,
        runtime_root=runtime_root,
        request_get=_healthy_fetch,
    )

    rendered = monitor.render_snapshot(snapshot, json_output=True)
    payload = json.loads(rendered)

    assert payload["overall_status"] == monitor.STATUS_READY
    assert set(payload) >= {
        "overall_status",
        "runtime",
        "provider",
        "launcher",
        "next_actions",
    }
    assert payload["runtime"]["status"] == monitor.STATUS_READY
    assert payload["provider"]["status"] == monitor.STATUS_READY
    assert (
        payload["launcher"]["startup_state"]["status"] == monitor.STATUS_READY
    )
    assert (
        payload["launcher"]["packaged_runtime"]["status"]
        == monitor.STATUS_READY
    )
