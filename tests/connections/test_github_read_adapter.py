"""No credentials or provider access: bounded GitHub transport and scope proof."""

import pytest
import requests

from guardian.connections.github import service as gh


def row(number=12, repository="owner/repo", pr=False):
    return {
        "number": number,
        "url": f"https://api.github.com/repos/{repository}/issues/{number}",
        "title": "Scoped issue",
        "body": "Details",
        "state": "open",
        "updated_at": "2026-11-13T00:00:00Z",
        **({"pull_request": {}} if pr else {}),
    }


def client():
    return gh.GitHubClient("test-only-secret", ["Owner/Repo"])


@pytest.mark.parametrize(
    "repository",
    [
        "elsewhere/repo",
        "owner/../repo",
        "https://github.com/owner/repo",
        "owner/repo?x=1",
        "owner/..",
        "owner/repo%2fextra",
    ],
)
def test_scope_denied_before_transport(monkeypatch, repository):
    monkeypatch.setattr(
        gh.requests, "get", lambda *a, **k: pytest.fail("unauthorized transport")
    )
    with pytest.raises(gh.GitHubScopeError):
        client().read_issue(repository=repository, number=1)


@pytest.mark.parametrize("grants", [[], ["owner/repo"] * 0, "owner/repo", ["owner/.."]])
def test_explicit_repository_grants_required(grants):
    with pytest.raises(gh.GitHubScopeError):
        gh.GitHubClient("test", grants)


@pytest.mark.parametrize(
    "query",
    [
        "repo:other/repo",
        'hello" OR repo:other/repo',
        "",
        "x" * 501,
        "hello\nworld",
        "hello\\world",
    ],
)
def test_search_query_cannot_inject_scope(monkeypatch, query):
    monkeypatch.setattr(
        gh.requests, "get", lambda *a, **k: pytest.fail("unauthorized transport")
    )
    with pytest.raises(gh.GitHubScopeError):
        client().search(repository="owner/repo", query=query)


def test_search_is_bounded_and_preserves_provenance(monkeypatch):
    calls = []

    def request(self, path, **kwargs):
        calls.append((path, kwargs))
        return {
            "items": [row(), row(13, pr=True)],
            "total_count": 1001,
            "incomplete_results": False,
        }

    monkeypatch.setattr(gh.GitHubClient, "_request_json", request)
    result = client().search(repository="Owner/Repo", query="release plan", limit=2)
    assert calls == [
        (
            "/search/issues",
            {
                "params": {
                    "q": 'repo:owner/repo "release plan"',
                    "page": 1,
                    "per_page": 2,
                }
            },
        )
    ]
    assert result["next_page"] == 2
    assert result["results_incomplete"] is True
    assert (
        result["results"][0]["external_url"]
        == "https://github.com/owner/repo/issues/12"
    )
    assert (
        result["results"][1]["external_url"] == "https://github.com/owner/repo/pull/13"
    )
    assert result["results"][1]["object_type"] == "pull_request"
    assert result["results"][0]["retrieved_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"items": None, "total_count": 0},
        {"items": [row(repository="other/repo")], "total_count": 1},
    ],
)
def test_invalid_or_cross_scope_search_response_fails(monkeypatch, payload):
    monkeypatch.setattr(gh.GitHubClient, "_request_json", lambda *a, **k: payload)
    with pytest.raises(gh.GitHubProviderError):
        client().search(repository="owner/repo", query="hello")


def test_read_retains_source_and_explicit_content_boundary(monkeypatch):
    payload = row(pr=True)
    payload["body"] = "x" * (gh.MAX_CONTENT_CHARS + 1)
    monkeypatch.setattr(gh.GitHubClient, "_request_json", lambda *a, **k: payload)
    result = client().read_issue(repository="owner/repo", number=12)
    assert len(result["content"]) == gh.MAX_CONTENT_CHARS
    assert result["content_truncated"] is True
    assert result["object"]["external_object_id"] == "owner/repo#12"
    assert result["content_scope"] == "issue_or_pull_request_body_only"


@pytest.mark.parametrize("number", [True, 0, -1, "12", 2**40])
def test_invalid_number_has_no_transport(monkeypatch, number):
    monkeypatch.setattr(
        gh.requests, "get", lambda *a, **k: pytest.fail("invalid transport")
    )
    with pytest.raises(gh.GitHubScopeError):
        client().read_issue(repository="owner/repo", number=number)


def test_read_rejects_wrong_object(monkeypatch):
    monkeypatch.setattr(gh.GitHubClient, "_request_json", lambda *a, **k: row(13))
    with pytest.raises(gh.GitHubProviderError):
        client().read_issue(repository="owner/repo", number=12)


@pytest.mark.parametrize(
    "status,error",
    [
        (302, gh.GitHubProviderError),
        (401, gh.GitHubAuthorizationError),
        (403, gh.GitHubAuthorizationError),
        (404, gh.GitHubObjectNotFoundError),
        (429, gh.GitHubProviderError),
        (500, gh.GitHubProviderError),
    ],
)
def test_safe_transport_failures(monkeypatch, status, error):
    calls = []

    class Response:
        status_code = status

        def json(self):
            pytest.fail("error payload should never be consumed")

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(gh.requests, "get", get)
    with pytest.raises(error) as exc:
        client().read_issue(repository="owner/repo", number=12)
    assert "secret" not in str(exc.value)
    assert calls[0][0] == "https://api.github.com/repos/owner/repo/issues/12"
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["timeout"] == 15


def test_transport_exception_suppresses_secret_chain(monkeypatch):
    def get(*args, **kwargs):
        raise requests.RequestException("test-only-secret")

    monkeypatch.setattr(gh.requests, "get", get)
    with pytest.raises(gh.GitHubTransportError) as exc:
        client().read_issue(repository="owner/repo", number=12)
    assert "test-only-secret" not in str(exc.value)
    assert exc.value.__suppress_context__ is True


def test_validation_checks_only_allowed_repositories(monkeypatch):
    calls = []

    def request(self, path, **kwargs):
        calls.append(path)
        return {"full_name": "Owner/Repo"}

    monkeypatch.setattr(gh.GitHubClient, "_request_json", request)
    client().validate()
    assert calls == ["/repos/owner/repo"]


@pytest.mark.parametrize(
    "page,limit", [(0, 25), (1, 0), (1, 51), (21, 50), (True, 25), (1, True)]
)
def test_invalid_pagination_has_no_transport(monkeypatch, page, limit):
    monkeypatch.setattr(
        gh.requests, "get", lambda *a, **k: pytest.fail("invalid transport")
    )
    with pytest.raises(gh.GitHubScopeError):
        client().search(
            repository="owner/repo", query="roadmap", page=page, limit=limit
        )


def test_success_transport_is_fixed_host_and_read_only(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return row()

    def get(url, **kwargs):
        assert url == "https://api.github.com/repos/owner/repo/issues/12"
        assert kwargs["headers"]["X-GitHub-Api-Version"] == gh.API_VERSION
        assert kwargs["allow_redirects"] is False
        return Response()

    monkeypatch.setattr(gh.requests, "get", get)
    result = client().read_issue(repository="owner/repo", number=12)
    assert result["content"] == "Details"
    assert result["content_truncated"] is False
    assert "test-only-secret" not in str(result)


def test_invalid_json_is_sanitized(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            raise ValueError("provider echo: test-only-secret")

    monkeypatch.setattr(gh.requests, "get", lambda *a, **k: Response())
    with pytest.raises(gh.GitHubProviderError) as exc:
        client().read_issue(repository="owner/repo", number=12)
    assert "test-only-secret" not in str(exc.value)
    assert exc.value.__suppress_context__ is True
