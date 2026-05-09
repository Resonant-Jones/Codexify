from guardian.server.app import app


def test_server_app_includes_health_and_media_routes():
    paths = {
        getattr(route, "path", None)
        for route in app.routes
        if getattr(route, "path", None)
    }

    assert "/health/chat" in paths
    assert "/api/health/chat" in paths
    assert "/api/embeddings" in paths
    assert "/api/media/upload/image" in paths
    assert "/api/media/upload/document" in paths
