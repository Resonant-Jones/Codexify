"""Bounded provider evidence must never look like an exhaustive read."""

import pytest

from guardian.connections.notion import service


def test_search_rejects_malformed_results(monkeypatch):
    monkeypatch.setattr(service.NotionClient, "_request_json", lambda *a, **k: {})
    with pytest.raises(service.NotionProviderError):
        service.NotionClient("test").search(query="roadmap", cursor=None, limit=1)


def test_transport_does_not_follow_redirects_or_expose_provider_errors(monkeypatch):
    captured = {}

    class Response:
        status_code = 302

        def json(self):
            raise AssertionError("redirect payload must not be consumed")

    def request(*args, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(service.requests, "request", request)
    with pytest.raises(service.NotionProviderError, match="unsuccessful response"):
        service.NotionClient("secret-for-test").validate()
    assert captured["allow_redirects"] is False
    assert captured["timeout"] == service.REQUEST_TIMEOUT_SECONDS


@pytest.mark.parametrize("boundary", ["depth", "blocks", "requests", "characters"])
def test_read_reports_each_traversal_limit(monkeypatch, boundary):
    monkeypatch.setattr(service, "MAX_BLOCK_DEPTH", 0 if boundary == "depth" else 2)
    monkeypatch.setattr(service, "MAX_BLOCKS", 1 if boundary == "blocks" else 200)
    monkeypatch.setattr(
        service, "MAX_BLOCK_REQUESTS", 1 if boundary == "requests" else 20
    )
    monkeypatch.setattr(
        service, "MAX_CONTENT_CHARS", 1 if boundary == "characters" else 50000
    )
    calls = []

    def request(self, method, path, **kwargs):
        calls.append(path)
        if path.startswith("/pages/"):
            return {"object": "page", "id": "page", "url": "https://www.notion.so/page"}
        return {
            "results": [
                {
                    "id": "child",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "hello"}]},
                    "has_children": boundary == "depth",
                }
            ],
            "has_more": boundary in {"blocks", "requests"},
            "next_cursor": "next",
        }

    monkeypatch.setattr(service.NotionClient, "_request_json", request)
    result = service.NotionClient("test").read_page("page")
    assert result["content_truncated"] is True
    assert result["object"]["external_url"] == "https://www.notion.so/page"
    assert len(calls) == 2


def test_empty_pages_have_a_total_request_bound(monkeypatch):
    calls = []

    def request(self, method, path, **kwargs):
        if path.startswith("/pages/"):
            return {"object": "page", "id": "page"}
        calls.append(path)
        return {"results": [], "has_more": True, "next_cursor": str(len(calls))}

    monkeypatch.setattr(service.NotionClient, "_request_json", request)
    result = service.NotionClient("test").read_page("page")
    assert len(calls) == service.MAX_BLOCK_REQUESTS
    assert result["content_truncated"] is True


def test_repeated_cursor_fails_boundedly(monkeypatch):
    calls = []

    def request(self, method, path, **kwargs):
        if path.startswith("/pages/"):
            return {"object": "page", "id": "page"}
        calls.append(path)
        return {"results": [], "has_more": True, "next_cursor": "same"}

    monkeypatch.setattr(service.NotionClient, "_request_json", request)
    with pytest.raises(service.NotionProviderError, match="pagination"):
        service.NotionClient("test").read_page("page")
    assert len(calls) == 2
