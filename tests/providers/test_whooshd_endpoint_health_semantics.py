"""Tests that prove Whoosh'd endpoint configuration and health semantics
without requiring a real daemon process or network call.
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardian.providers.whooshd_sidecar import (
    Ownership,
    WhooshdSidecar,
    WhooshdState,
    WhooshdStatus,
    _map_runtime_state,
)


class TestEndpointConfiguration:
    def test_base_url_derives_from_settings_host_port(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)
        assert sidecar.base_url == "http://127.0.0.1:8000"

    def test_base_url_uses_provided_host_port_dynamically(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_HOST = "0.0.0.0"
        settings.WHOOSHD_PORT = 9999
        sidecar = WhooshdSidecar(settings=settings)
        assert sidecar.base_url == "http://0.0.0.0:9999"


class TestIsManagedConfig:
    def test_is_managed_enabled_true_when_WHOOSHD_MANAGED(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_MANAGED = True
        sidecar = WhooshdSidecar(settings=settings)
        assert sidecar.is_managed_enabled is True

    def test_is_managed_enabled_false_by_default(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_MANAGED = False
        sidecar = WhooshdSidecar(settings=settings)
        assert sidecar.is_managed_enabled is False


class TestWhooshdConfigured:
    def test_is_whooshd_configured_true_when_vendor_is_whooshd(self) -> None:
        settings = MagicMock()
        settings.LOCAL_PROVIDER_VENDOR = "whooshd"
        sidecar = WhooshdSidecar(settings=settings)
        assert sidecar.is_whooshd_configured is True

    def test_is_whooshd_configured_false_for_other_vendor(self) -> None:
        settings = MagicMock()
        settings.LOCAL_PROVIDER_VENDOR = "ollama"
        sidecar = WhooshdSidecar(settings=settings)
        assert sidecar.is_whooshd_configured is False

    def test_is_whooshd_configured_false_for_empty_vendor(self) -> None:
        settings = MagicMock()
        settings.LOCAL_PROVIDER_VENDOR = ""
        sidecar = WhooshdSidecar(settings=settings)
        assert sidecar.is_whooshd_configured is False


class TestDetectHealthFailure:
    @pytest.mark.asyncio
    async def test_detect_returns_offline_when_unreachable(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            status = await sidecar.detect()
            assert status.state == WhooshdState.OFFLINE
            assert "not reachable" in status.detail

    @pytest.mark.asyncio
    async def test_detect_returns_error_when_health_non_200(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            status = await sidecar.detect()
            assert status.state == WhooshdState.ERROR
            assert "500" in status.detail

    @pytest.mark.asyncio
    async def test_detect_health_probe_polled_first(self) -> None:
        """Verify that /health is tried before /v1/models or /api/tags."""
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await sidecar.detect()
            calls = [c[0][0] for c in mock_client.get.call_args_list if c[0]]
            assert calls[0] == "http://127.0.0.1:8000/health"


class TestDetectHealthSuccess:
    @pytest.mark.asyncio
    async def test_detect_with_runtime_sets_state_from_runtime(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            def make_response(url: str, *a: object, **kw: object) -> MagicMock:
                r = MagicMock()
                r.status_code = 200
                if url.endswith("/health/runtime"):
                    r.json = MagicMock(return_value={
                        "session": {"session_id": "s1", "pid": 123},
                        "runtimes": {
                            "mlx": {
                                "state": "ready",
                                "active_model": "test-model",
                                "configured_model": "test-model",
                            }
                        },
                    })
                elif url.endswith("/v1/models"):
                    r.json = MagicMock(return_value={"data": [{"id": "test-model"}]})
                elif url.endswith("/api/tags"):
                    r.json = MagicMock(return_value={"models": [{"name": "test-model"}]})
                return r

            mock_client.get = AsyncMock(side_effect=make_response)
            mock_client_cls.return_value = mock_client

            status = await sidecar.detect()
            assert status.state == WhooshdState.READY
            assert status.active_model == "test-model"
            assert status.session_id == "s1"
            assert status.pid == 123

    @pytest.mark.asyncio
    async def test_detect_stub_runtime_sets_runtime_available(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            def make_response(url: str, *a: object, **kw: object) -> MagicMock:
                r = MagicMock()
                r.status_code = 200
                if url.endswith("/health/runtime"):
                    r.json = MagicMock(return_value={
                        "session": {"session_id": "s2"},
                        "runtimes": {"stub": {"state": "starting"}},
                    })
                return r

            mock_client.get = AsyncMock(side_effect=make_response)
            mock_client_cls.return_value = mock_client

            status = await sidecar.detect()
            assert status.state == WhooshdState.RUNTIME_AVAILABLE
            assert status.active_model == "stub-model"


class TestDetectPopulatesModelInventory:
    @pytest.mark.asyncio
    async def test_detect_polls_v1_models(self) -> None:
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            def make_response(url: str, *a: object, **kw: object) -> MagicMock:
                r = MagicMock()
                r.status_code = 200
                if url.endswith("/health/runtime"):
                    r.json = MagicMock(return_value={
                        "session": {},
                        "runtimes": {"mlx": {"state": "ready"}},
                    })
                elif url.endswith("/v1/models"):
                    r.json = MagicMock(return_value={
                        "data": [{"id": "m1"}, {"id": "m2"}]
                    })
                return r

            mock_client.get = AsyncMock(side_effect=make_response)
            mock_client_cls.return_value = mock_client

            status = await sidecar.detect()
            assert status.models == ["m1", "m2"]


class TestNoRealProcessOrNetwork:
    def test_whooshdstatus_has_no_side_effects(self) -> None:
        status = WhooshdStatus(base_url="http://localhost:8000")
        assert status.state == WhooshdState.OFFLINE
        assert status.ownership == Ownership.NONE
        assert status.pid is None

    def test_whooshdsidecar_constructor_does_not_launch(self) -> None:
        sidecar = WhooshdSidecar()
        assert sidecar._process is None
        assert sidecar._launched_pid is None


class TestReleaseBoundary:
    @pytest.mark.asyncio
    async def test_health_success_does_not_imply_model_inventory_proof(self) -> None:
        """Endpoint health proves reachability — not model inventory correctness."""
        # The detect() method polls /health → /health/runtime → /v1/models.
        # Health success is a prerequisite for model inventory, not a substitute.
        settings = MagicMock()
        settings.WHOOSHD_HOST = "127.0.0.1"
        settings.WHOOSHD_PORT = 8000
        sidecar = WhooshdSidecar(settings=settings)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            def make_response(url: str, *a: object, **kw: object) -> MagicMock:
                r = MagicMock()
                r.status_code = 200
                if url.endswith("/health/runtime"):
                    r.json = MagicMock(return_value={
                        "session": {"session_id": "s1"},
                        "runtimes": {"mlx": {"state": "ready", "active_model": "m1", "configured_model": "m1"}},
                    })
                elif url.endswith("/v1/models"):
                    r.json = MagicMock(return_value={"data": [{"id": "m1"}]})
                return r

            mock_client.get = AsyncMock(side_effect=make_response)
            mock_client_cls.return_value = mock_client

            status = await sidecar.detect()
            # Health is ready — model list populated but not verified
            assert status.state == WhooshdState.READY
            assert status.models == ["m1"]
            # This proves models were returned — NOT that the operator can see them,
            # NOT that model identity matches preset, NOT that context works.
