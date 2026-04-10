"""Tests for executor health surface."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from guardian.core.executors.health import (
    ExecutorHealth,
    _derive_availability,
    _detect_auth_state,
    _resolve_binary_path,
    get_all_executor_health,
    get_executor_health,
)
from guardian.core.executors.registry import (
    ExecutorId,
    get_executor_entry,
    get_executor_registry,
)
from guardian.protocol_tokens import (
    ExecutorAuthState,
    ExecutorAvailabilityState,
)


class TestResolveBinaryPath:
    def test_not_installed_returns_false_and_none(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(
            os.environ, {"CODEXIFY_CODEX_BIN": "/nonexistent/binary"}
        ):
            installed, path = _resolve_binary_path(entry)
        assert installed is False
        assert path is None

    def test_installed_via_env_var_returns_path(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(os.environ, {"CODEXIFY_CODEX_BIN": "python3"}):
            installed, path = _resolve_binary_path(entry)
        assert installed is True
        assert path == "python3"


class TestDetectAuthState:
    def test_unknown_when_binary_not_configured(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(os.environ, {}, clear=True):
            state, detail = _detect_auth_state(entry)
        assert state == ExecutorAuthState.UNKNOWN.value
        assert "not configured" in detail

    def test_unknown_when_binary_not_on_path(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(
            os.environ, {"CODEXIFY_CODEX_BIN": "/nonexistent/binary"}
        ):
            state, detail = _detect_auth_state(entry)
        assert state == ExecutorAuthState.UNKNOWN.value
        assert "not found" in detail


class TestDeriveAvailability:
    def test_not_installed_yields_not_installed_state(self) -> None:
        state, detail = _derive_availability(
            False, ExecutorAuthState.AUTHENTICATED.value
        )
        assert state == ExecutorAvailabilityState.NOT_INSTALLED.value

    def test_installed_authenticated_yields_ready(self) -> None:
        state, detail = _derive_availability(
            True, ExecutorAuthState.AUTHENTICATED.value
        )
        assert state == ExecutorAvailabilityState.READY.value
        assert detail is None

    def test_installed_unknown_auth_yields_degraded(self) -> None:
        state, detail = _derive_availability(
            True, ExecutorAuthState.UNKNOWN.value
        )
        assert state == ExecutorAvailabilityState.DEGRADED.value
        assert detail is not None

    def test_installed_unauthenticated_yields_unavailable(self) -> None:
        state, detail = _derive_availability(
            True, ExecutorAuthState.UNAUTHENTICATED.value
        )
        assert state == ExecutorAvailabilityState.UNAVAILABLE.value


class TestGetExecutorHealth:
    def test_health_model_contains_required_fields(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(
            os.environ, {"CODEXIFY_CODEX_BIN": "/nonexistent/binary"}
        ):
            health = get_executor_health(entry)
        assert isinstance(health, ExecutorHealth)
        assert health.executor_id == "codex"
        assert health.label == "Codex CLI"
        assert health.release_posture == "official"
        assert health.installed is False
        assert health.binary_path is None
        assert health.auth_state == ExecutorAuthState.UNKNOWN.value
        assert health.status_detail is not None

    def test_health_preserves_registry_posture(self) -> None:
        entry = get_executor_entry(ExecutorId.OPENCODE)
        with patch.dict(
            os.environ, {"CODEXIFY_OPENCODE_BIN": "/nonexistent/binary"}
        ):
            health = get_executor_health(entry)
        assert health.release_posture == "optional"

    def test_installed_executor_reports_binary_path(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(os.environ, {"CODEXIFY_CODEX_BIN": "python3"}):
            health = get_executor_health(entry)
        assert health.installed is True
        assert health.binary_path == "python3"

    def test_availability_computed_from_install_and_auth(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(
            os.environ, {"CODEXIFY_CODEX_BIN": "/nonexistent/binary"}
        ):
            health = get_executor_health(entry)
        assert (
            health.availability_state
            == ExecutorAvailabilityState.NOT_INSTALLED.value
        )


class TestGetAllExecutorHealth:
    def test_returns_list_with_all_registry_executors(self) -> None:
        registry = get_executor_registry()
        with patch.dict(os.environ, {}, clear=True):
            all_health = get_all_executor_health()
        assert len(all_health) == len(registry)
        executor_ids = {h.executor_id for h in all_health}
        assert executor_ids == {"codex", "claude_code", "opencode"}

    def test_each_health_has_correct_structure(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            all_health = get_all_executor_health()
        for health in all_health:
            assert hasattr(health, "executor_id")
            assert hasattr(health, "label")
            assert hasattr(health, "release_posture")
            assert hasattr(health, "installed")
            assert hasattr(health, "binary_path")
            assert hasattr(health, "auth_state")
            assert hasattr(health, "availability_state")
            assert hasattr(health, "supports_local_models")
            assert hasattr(health, "supports_gateway_routing")
            assert hasattr(health, "supports_direct_provider_config")
            assert hasattr(health, "supported_auth_modes")
            assert hasattr(health, "status_detail")

    def test_supported_auth_modes_from_registry(self) -> None:
        entry = get_executor_entry(ExecutorId.OPENCODE)
        with patch.dict(
            os.environ, {"CODEXIFY_OPENCODE_BIN": "/nonexistent/binary"}
        ):
            health = get_executor_health(entry)
        assert "direct_provider" in health.supported_auth_modes
        assert "local_model" in health.supported_auth_modes
        assert "gateway_base_url" in health.supported_auth_modes


class TestExecutorHealthToDict:
    def test_to_dict_produces_serializable_dict(self) -> None:
        entry = get_executor_entry(ExecutorId.CODEX)
        with patch.dict(
            os.environ, {"CODEXIFY_CODEX_BIN": "/nonexistent/binary"}
        ):
            health = get_executor_health(entry)
        d = health.to_dict()
        assert isinstance(d, dict)
        assert d["executor_id"] == "codex"
        assert d["installed"] is False
        assert d["auth_state"] == "unknown"
