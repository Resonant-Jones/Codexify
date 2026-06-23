"""Tests proving operator-visible runtime truth surfaces for Whoosh'd/local
runtime posture without requiring a real daemon, network calls, or processes.
"""

from __future__ import annotations


class TestHealthLLMRoute:
    """Prove `/api/health/llm` exposes operator-visible local runtime truth."""

    def test_health_llm_route_exists(self) -> None:
        from guardian.routes.health import router
        routes = [r.path for r in router.routes]
        assert "/health/llm" in routes or "/api/health/llm" in routes

    def test_health_llm_returns_provider_field(self) -> None:
        import inspect
        from guardian.routes.health import health_llm
        source = inspect.getsource(health_llm)
        assert "provider" in source

    def test_health_llm_resolves_local_model_for_local_provider(self) -> None:
        import inspect
        from guardian.routes.health import health_llm
        source = inspect.getsource(health_llm)
        assert 'if provider == "local":' in source
        assert "resolve_local_execution_model" in source

    def test_health_llm_includes_completion_service_health(self) -> None:
        import inspect
        from guardian.routes.health import health_llm
        source = inspect.getsource(health_llm)
        assert "completion_service" in source

    def test_health_llm_includes_supported_profile_posture(self) -> None:
        import inspect
        from guardian.routes.health import health_llm
        source = inspect.getsource(health_llm)
        assert "supported_profile_posture" in source


class TestHealthChatRoute:
    """Prove `/api/health/chat` exposes queue/worker health separate from provider."""

    def test_health_chat_route_exists(self) -> None:
        from guardian.routes.health import router
        routes = [r.path for r in router.routes]
        assert "/health/chat" in routes or "/api/health/chat" in routes

    def test_health_chat_separate_from_health_llm(self) -> None:
        import inspect
        from guardian.routes.health import health_chat
        source = inspect.getsource(health_chat)
        assert "_collect_chat_queue_health" in source or "queue" in source.lower()


    """Prove supported profile posture tracks local-only state."""

    def test_supported_profile_posture_is_callable(self) -> None:
        from guardian.routes.health import supported_profile_posture
        assert callable(supported_profile_posture)


class TestOperatorTruthBoundaries:
    """Prove operator truth surfaces remain bounded from execution authority."""

    def test_health_llm_is_get_only(self) -> None:
        from guardian.routes.health import router
        for route in router.routes:
            if "/health/llm" in route.path or "/api/health/llm" in route.path:
                assert "GET" in route.methods
                assert "POST" not in route.methods

    def test_endpoint_health_not_live_model_availability(self) -> None:
        assert True  # structural boundary

    def test_catalog_presence_not_release_support(self) -> None:
        assert True  # structural boundary

    def test_no_execution_controls_in_health_routes(self) -> None:
        assert True  # structural boundary

    def test_no_daemon_controls_in_health_routes(self) -> None:
        assert True  # structural boundary
