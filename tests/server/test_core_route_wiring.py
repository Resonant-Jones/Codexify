import importlib


def _collect_route_paths(routes, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for route in routes:
        route_path = getattr(route, "path", None)
        if route_path:
            paths.add(f"{prefix}{route_path}")
            continue

        included = getattr(route, "original_router", None)
        include_context = getattr(route, "include_context", None)
        if included is None or include_context is None:
            continue
        paths.update(
            _collect_route_paths(
                getattr(included, "routes", []),
                f"{prefix}{getattr(include_context, 'prefix', '')}",
            )
        )
    return paths


def test_server_app_includes_health_and_media_routes(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))
    from guardian.server import app as server_app

    importlib.reload(server_app)
    paths = _collect_route_paths(server_app.app.routes)

    assert "/health/chat" in paths
    assert "/api/health/chat" in paths
    assert "/api/embeddings" in paths
    assert "/api/media/upload/image" in paths
    assert "/api/media/upload/document" in paths
