"""Tests for scripts/ops/monitor_desktop_runtime.py.

These tests use monkeypatching to simulate runtime conditions without
requiring a live Docker Compose stack or real HTTP responses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure the script is importable from the repo root
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts" / "ops"))

# Import the module directly
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "monitor_desktop_runtime",
    _ROOT / "scripts" / "ops" / "monitor_desktop_runtime.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules[
    _spec.name
] = _mod  # required so dataclass _is_type sees the module in sys.modules
_spec.loader.exec_module(_mod)


HealthStatus = _mod.HealthStatus
HttpSurfaceResult = _mod.HttpSurfaceResult
LauncherArtifactResult = _mod.LauncherArtifactResult
MonitorSummary = _mod.MonitorSummary
DesktopRuntimeMonitor = _mod.DesktopRuntimeMonitor
_codexify_app_support_root = _mod._codexify_app_support_root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_http_result(
    url: str,
    status: HealthStatus,
    http_status_code: int | None = 200,
    error: str | None = None,
) -> HttpSurfaceResult:
    return HttpSurfaceResult(
        url=url,
        status=status,
        http_status_code=http_status_code,
        response_body={"status": "ok"}
        if status == HealthStatus.READY
        else None,
        error=error,
    )


def make_artifact_result(
    path: str,
    status: HealthStatus,
    detail: str | None = None,
) -> LauncherArtifactResult:
    return LauncherArtifactResult(path=path, status=status, detail=detail)


# ---------------------------------------------------------------------------
# HealthStatus enumSanity
# ---------------------------------------------------------------------------


class TestHealthStatusVocabulary:
    def test_all_status_values_are_strings(self) -> None:
        for member in HealthStatus:
            assert isinstance(member.value, str)

    def test_exhaustive_status_set(self) -> None:
        expected = {
            "ready",
            "degraded",
            "not_ready",
            "unreachable",
            "missing_artifact",
        }
        actual = {m.value for m in HealthStatus}
        assert actual == expected


# ---------------------------------------------------------------------------
# HttpSurfaceResult
# ---------------------------------------------------------------------------


class TestHttpSurfaceResult:
    def test_is_healthy_enough_ready(self) -> None:
        r = make_http_result("http://localhost/health", HealthStatus.READY)
        assert r.is_healthy_enough() is True

    def test_is_healthy_enough_degraded(self) -> None:
        r = make_http_result("http://localhost/health", HealthStatus.DEGRADED)
        assert r.is_healthy_enough() is True

    def test_is_healthy_enough_not_ready(self) -> None:
        r = make_http_result("http://localhost/health", HealthStatus.NOT_READY)
        assert r.is_healthy_enough() is True

    def test_is_healthy_enough_unreachable(self) -> None:
        r = make_http_result(
            "http://localhost/health",
            HealthStatus.UNREACHABLE,
            http_status_code=None,
            error="connection refused",
        )
        assert r.is_healthy_enough() is False

    def test_is_healthy_enough_missing_artifact(self) -> None:
        # missing_artifact is not an HTTP status — included for completeness
        r = HttpSurfaceResult(
            url="http://localhost/health",
            status=HealthStatus.MISSING_ARTIFACT,
        )
        assert r.is_healthy_enough() is False


# ---------------------------------------------------------------------------
# _classify_health_body
# ---------------------------------------------------------------------------


class TestClassifyHealthBody:
    _classify = staticmethod(_mod._classify_health_body)

    def test_health_ok(self) -> None:
        assert self._classify("/health", {"status": "ok"}) == HealthStatus.READY

    def test_health_degraded(self) -> None:
        assert (
            self._classify("/health", {"status": "degraded"})
            == HealthStatus.DEGRADED
        )

    def test_health_unhealthy(self) -> None:
        assert (
            self._classify("/health", {"status": "unhealthy"})
            == HealthStatus.UNREACHABLE
        )

    def test_health_starting(self) -> None:
        assert (
            self._classify("/health", {"status": "starting"})
            == HealthStatus.NOT_READY
        )

    def test_health_chat_queue_healthy(self) -> None:
        assert (
            self._classify(
                "/health/chat",
                {"queue_health": "healthy", "workers_alive": True},
            )
            == HealthStatus.READY
        )

    def test_health_chat_workers_dead(self) -> None:
        assert (
            self._classify(
                "/health/chat",
                {"queue_health": "ok", "workers_alive": False},
            )
            == HealthStatus.DEGRADED
        )

    def test_health_chat_queue_unhealthy(self) -> None:
        assert (
            self._classify("/health/chat", {"queue_health": "unhealthy"})
            == HealthStatus.UNREACHABLE
        )

    def test_health_llm_provider_ready(self) -> None:
        assert (
            self._classify(
                "/api/health/llm",
                {"provider_runtime": "ready", "provider": "local"},
            )
            == HealthStatus.READY
        )

    def test_health_llm_warming(self) -> None:
        assert (
            self._classify(
                "/api/health/llm", {"provider_runtime": "model_warming"}
            )
            == HealthStatus.NOT_READY
        )

    def test_health_llm_offline(self) -> None:
        assert (
            self._classify("/api/health/llm", {"provider_runtime": "offline"})
            == HealthStatus.UNREACHABLE
        )

    def test_health_llm_degraded(self) -> None:
        assert (
            self._classify("/api/health/llm", {"provider_runtime": "degraded"})
            == HealthStatus.DEGRADED
        )

    def test_health_retrieval_ok(self) -> None:
        assert (
            self._classify("/api/health/retrieval", {"vector_health": "ok"})
            == HealthStatus.READY
        )

    def test_health_retrieval_unavailable(self) -> None:
        assert (
            self._classify(
                "/api/health/retrieval", {"vector_health": "unavailable"}
            )
            == HealthStatus.UNREACHABLE
        )

    def test_llm_catalog_with_models(self) -> None:
        assert (
            self._classify(
                "/api/llm/catalog",
                {"models": [{"name": "gemma4", "provider": "local"}]},
            )
            == HealthStatus.READY
        )

    def test_fallback_to_ready_for_unknown_body(self) -> None:
        # No known health fields — monitor should not crash; treat as ready
        assert self._classify("/unknown", {"foo": "bar"}) == HealthStatus.READY


# ---------------------------------------------------------------------------
# _probe_launcher_artifact
# ---------------------------------------------------------------------------


class TestProbeLauncherArtifact:
    def test_missing_artifact(self, tmp_path: Path) -> None:
        result = _mod._probe_launcher_artifact(
            tmp_path / "nonexistent.json", is_file=True
        )
        assert result.status == HealthStatus.MISSING_ARTIFACT

    def test_valid_json_file(self, tmp_path: Path) -> None:
        artifact = tmp_path / ".codexify-launcher-startup-state.json"
        artifact.write_text('{"setup_complete": true}', encoding="utf-8")
        result = _mod._probe_launcher_artifact(artifact, is_file=True)
        assert result.status == HealthStatus.READY
        assert result.detail == "present"

    def test_malformed_json_file(self, tmp_path: Path) -> None:
        artifact = tmp_path / ".codexify-launcher-startup-state.json"
        artifact.write_text("not valid json {", encoding="utf-8")
        result = _mod._probe_launcher_artifact(artifact, is_file=True)
        assert result.status == HealthStatus.DEGRADED
        assert "not valid JSON" in result.detail

    def test_directory_when_file_expected(self, tmp_path: Path) -> None:
        artifact = tmp_path / ".codexify-packaged-runtime"
        artifact.mkdir()
        result = _mod._probe_launcher_artifact(artifact, is_file=True)
        assert result.status == HealthStatus.DEGRADED
        assert "expected file but found directory" in result.detail

    def test_directory_marker_present(self, tmp_path: Path) -> None:
        artifact = tmp_path / ".codexify-packaged-runtime"
        artifact.mkdir()
        result = _mod._probe_launcher_artifact(artifact, is_file=False)
        assert result.status == HealthStatus.READY
        assert result.detail == "directory present"


# ---------------------------------------------------------------------------
# _derive_overall_status
# ---------------------------------------------------------------------------


class TestDeriveOverallStatus:
    def _derive(self, *statuses: tuple[str, HealthStatus]) -> HealthStatus:
        """Build surface dicts and call _derive_overall_status."""
        runtime = {
            name: make_http_result(f"http://x/{name}", s)
            for name, s in statuses
        }
        artifacts: dict[str, LauncherArtifactResult] = {}
        return _mod.DesktopRuntimeMonitor()._derive_overall_status(
            runtime, artifacts
        )

    def test_all_ready(self) -> None:
        assert (
            self._derive(
                ("health", HealthStatus.READY),
                ("health_chat", HealthStatus.READY),
            )
            == HealthStatus.READY
        )

    def test_one_degraded_wins_over_ready(self) -> None:
        assert (
            self._derive(
                ("health", HealthStatus.READY),
                ("health_chat", HealthStatus.DEGRADED),
            )
            == HealthStatus.DEGRADED
        )

    def test_unreachable_wins_over_degraded(self) -> None:
        assert (
            self._derive(
                ("health", HealthStatus.DEGRADED),
                ("health_chat", HealthStatus.UNREACHABLE),
            )
            == HealthStatus.UNREACHABLE
        )

    def test_missing_artifact_wins_over_not_ready(self) -> None:
        runtime = {
            "health": make_http_result("http://x", HealthStatus.NOT_READY)
        }
        artifacts = {
            ".codexify-launcher-startup-state.json": make_artifact_result(
                "/path", HealthStatus.MISSING_ARTIFACT
            )
        }
        assert (
            _mod.DesktopRuntimeMonitor()._derive_overall_status(
                runtime, artifacts
            )
            == HealthStatus.MISSING_ARTIFACT
        )


# ---------------------------------------------------------------------------
# _derive_next_actions
# ---------------------------------------------------------------------------


class TestDeriveNextActions:
    def _actions(
        self,
        runtime_statuses: dict[str, HealthStatus],
        artifact_statuses: dict[str, HealthStatus],
    ) -> list[str]:
        runtime = {
            name: make_http_result(f"http://localhost/{name}", s)
            for name, s in runtime_statuses.items()
        }
        artifacts = {
            name: make_artifact_result(f"/app/{name}", s)
            for name, s in artifact_statuses.items()
        }
        return _mod.DesktopRuntimeMonitor()._derive_next_actions(
            runtime, artifacts
        )

    def test_no_actions_when_all_healthy(self) -> None:
        actions = self._actions(
            runtime_statuses={"health": HealthStatus.READY},
            artifact_statuses={
                ".codexify-launcher-startup-state.json": HealthStatus.READY
            },
        )
        assert len(actions) == 1
        assert "No immediate action required" in actions[0]

    def test_action_for_unreachable_runtime(self) -> None:
        actions = self._actions(
            runtime_statuses={"health": HealthStatus.UNREACHABLE},
            artifact_statuses={},
        )
        assert any("unreachable" in a and "health" in a for a in actions)

    def test_action_for_missing_artifacts(self) -> None:
        actions = self._actions(
            runtime_statuses={},
            artifact_statuses={
                ".codexify-launcher-startup-state.json": HealthStatus.MISSING_ARTIFACT
            },
        )
        assert any(
            "not found" in a.lower() and "launcher" in a.lower()
            for a in actions
        )

    def test_action_for_degraded_artifacts(self) -> None:
        actions = self._actions(
            runtime_statuses={},
            artifact_statuses={
                ".codexify-runtime-manifest.json": HealthStatus.DEGRADED
            },
        )
        assert any("degraded" in a.lower() for a in actions)


# ---------------------------------------------------------------------------
# DesktopRuntimeMonitor.run_once — full integration with mocked HTTP + artifacts
# ---------------------------------------------------------------------------


class TestMonitorRunOnce:
    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_healthy_runtime_all_artifacts_present(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        mock_http.return_value = make_http_result(
            "http://localhost/health", HealthStatus.READY
        )
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.READY, "present"
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()

        assert summary.overall_status == HealthStatus.READY
        assert all(
            r.status == HealthStatus.READY for r in summary.runtime.values()
        )
        assert all(
            r.status == HealthStatus.READY
            for r in summary.launcher_artifacts.values()
        )

    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_healthy_runtime_artifact_missing(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        mock_http.return_value = make_http_result(
            "http://localhost/health", HealthStatus.READY
        )
        mock_artifact.return_value = make_artifact_result(
            "/app/.codexify-launcher-startup-state.json",
            HealthStatus.MISSING_ARTIFACT,
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()

        assert summary.overall_status == HealthStatus.MISSING_ARTIFACT
        assert any(
            a.status == HealthStatus.MISSING_ARTIFACT
            for a in summary.launcher_artifacts.values()
        )

    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_one_runtime_surface_unreachable(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        # Return READY for most, UNREACHABLE for health_llm
        def http_side_effect(url: str, timeout: float = 5.0) -> HttpSurfaceResult:  # type: ignore[unused-var]
            if "llm" in url:
                return make_http_result(
                    url,
                    HealthStatus.UNREACHABLE,
                    http_status_code=None,
                    error="connection refused",
                )
            return make_http_result(url, HealthStatus.READY)

        mock_http.side_effect = http_side_effect
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.READY
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()

        assert summary.overall_status == HealthStatus.UNREACHABLE
        llm_result = summary.runtime.get("health_llm")
        assert llm_result is not None
        assert llm_result.status == HealthStatus.UNREACHABLE

    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_degraded_provider_while_backend_reachable(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        def http_side_effect(url: str, timeout: float = 5.0) -> HttpSurfaceResult:  # type: ignore[unused-var]
            if "llm" in url:
                return make_http_result(
                    url,
                    HealthStatus.DEGRADED,
                    http_status_code=200,
                )
            return make_http_result(url, HealthStatus.READY)

        mock_http.side_effect = http_side_effect
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.READY
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()

        # DEGRADED on llm should not make overall UNREACHABLE
        assert summary.overall_status == HealthStatus.DEGRADED
        llm_result = summary.runtime.get("health_llm")
        assert llm_result is not None
        assert llm_result.status == HealthStatus.DEGRADED


# ---------------------------------------------------------------------------
# JSON output contract
# ---------------------------------------------------------------------------


class TestJsonOutputContract:
    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_json_contains_required_keys(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        mock_http.return_value = make_http_result(
            "http://localhost/health", HealthStatus.READY
        )
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.READY
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()
        d = summary.as_dict()

        assert "overall_status" in d
        assert "runtime" in d
        assert "launcher_artifacts" in d
        assert "next_actions" in d
        assert isinstance(d["next_actions"], list)

    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_json_runtime_status_is_string(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        mock_http.return_value = make_http_result(
            "http://localhost/health", HealthStatus.READY
        )
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.READY
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()
        d = summary.as_dict()

        for name, surf in d["runtime"].items():
            assert isinstance(surf["status"], str)
            assert surf["status"] in {s.value for s in HealthStatus}

    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_json_launcher_status_is_string(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        mock_http.return_value = make_http_result(
            "http://localhost/health", HealthStatus.READY
        )
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.READY
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()
        d = summary.as_dict()

        for name, art in d["launcher_artifacts"].items():
            assert isinstance(art["status"], str)
            assert art["status"] in {s.value for s in HealthStatus}

    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_json_overall_status_is_valid(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        mock_http.return_value = make_http_result(
            "http://localhost/health", HealthStatus.READY
        )
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.READY
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()
        d = summary.as_dict()

        assert d["overall_status"] in {s.value for s in HealthStatus}


# ---------------------------------------------------------------------------
# MonitorSummary next_actions are advisory only (never auto-remediating)
# ---------------------------------------------------------------------------


class TestNextActionsAreAdvisory:
    @patch.object(_mod, "_probe_http_surface")
    @patch.object(_mod, "_probe_launcher_artifact")
    def test_next_actions_do_not_include_restart_or_patch(
        self,
        mock_artifact: MagicMock,
        mock_http: MagicMock,
    ) -> None:
        mock_http.return_value = make_http_result(
            "http://localhost/health",
            HealthStatus.UNREACHABLE,
            http_status_code=None,
            error="refused",
        )
        mock_artifact.return_value = make_artifact_result(
            "/app/x", HealthStatus.MISSING_ARTIFACT
        )

        monitor = DesktopRuntimeMonitor(
            backend_base_url="http://localhost:8888"
        )
        summary = monitor.run_once()

        for action in summary.next_actions:
            # Verify the monitor only advises, never commands auto-remediation
            assert not any(
                keyword in action.lower()
                for keyword in [
                    "restart",
                    "patch",
                    "apply",
                    "auto",
                    "fix",
                    "repair",
                    "rewrite",
                    "migrate",
                    "commit",
                ]
            ), f"Action contains auto-remediation keyword: {action}"
