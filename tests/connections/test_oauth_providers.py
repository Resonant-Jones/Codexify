"""Protocol-only fixtures. No real credentials or provider network calls."""

import json
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, Mock

import pytest

from guardian.connections import oauth_providers as oauth


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    request = MagicMock(side_effect=AssertionError("unexpected network"))
    monkeypatch.setattr(oauth.requests, "request", request)
    return request


def config(provider="github", redirect="https://example.test/oauth/callback"):
    return oauth.OAuthConfig(provider, "client", "secret-fixture", redirect)


def payload(provider="github"):
    result = {
        "access_token": "access-fixture",
        "refresh_token": "refresh-fixture",
        "token_type": "bearer",
    }
    if provider == "github":
        result.update(
            access_token="ghu_access-fixture",
            refresh_token="ghr_refresh-fixture",
            expires_in=28800,
            refresh_token_expires_in=15897600,
            scope="",
        )
    else:
        result.update(
            workspace_id="00000000-0000-0000-0000-000000000001",
            bot_id="00000000-0000-0000-0000-000000000002",
        )
    return result


def respond(request, data, status=200):
    response = Mock(status_code=status)
    response.iter_content.return_value = [json.dumps(data).encode()]
    request.side_effect = None
    request.return_value.__enter__.return_value = response
    return response


@pytest.mark.parametrize("provider", ["github", "notion"])
def test_authorize_fixed_host_and_no_secrets(provider):
    url = oauth.authorization_url(
        config(provider), state="opaque-state", code_challenge="A" * 43
    )
    parsed = urlsplit(url)
    assert parsed.hostname == (
        "github.com" if provider == "github" else "api.notion.com"
    )
    query = parse_qs(parsed.query)
    assert query["state"] == ["opaque-state"]
    assert "secret-fixture" not in url
    if provider == "github":
        assert query["scope"] == ["offline_access"]
        assert query["code_challenge_method"] == ["S256"]
    else:
        assert query["owner"] == ["user"]
        assert "scope" not in query


@pytest.mark.parametrize("provider", ["github", "notion"])
def test_code_exchange_and_rotating_refresh(provider, no_network):
    respond(no_network, payload(provider))
    tokens = oauth.exchange_code(
        config(provider), code="code-fixture", code_verifier="A" * 43
    )
    assert (
        tokens.access_token == payload(provider)["access_token"]
        and tokens.refresh_token == payload(provider)["refresh_token"]
    )
    assert "fixture" not in repr(tokens)
    call = no_network.call_args
    assert call.kwargs["allow_redirects"] is False and call.kwargs["stream"] is True
    assert call.kwargs["timeout"] == 15
    body = call.kwargs["data" if provider == "github" else "json"]
    assert body["code"] == "code-fixture"
    if provider == "github":
        assert body["code_verifier"] == "A" * 43
    else:
        assert call.kwargs["auth"] == ("client", "secret-fixture")
        assert set(tokens.metadata) == {"workspace_id", "bot_id"}
    new_refresh = "ghr_rotated-fixture" if provider == "github" else "rotated-fixture"
    rotated = payload(provider) | {"refresh_token": new_refresh}
    respond(no_network, rotated)
    assert (
        oauth.refresh_tokens(
            config(provider), refresh_token="old-fixture"
        ).refresh_token
        == new_refresh
    )
    assert (
        no_network.call_args.kwargs["data" if provider == "github" else "json"][
            "grant_type"
        ]
        == "refresh_token"
    )


@pytest.mark.parametrize(
    "redirect",
    [
        "http://evil.test/cb",
        "https://user:pass@example.test/cb",
        "https://example.test/cb#x",
        "https://example.test/cb?next=evil",
        "javascript:alert(1)",
        "https://example.test:bad/cb",
    ],
)
def test_unsafe_redirect_rejected(redirect):
    with pytest.raises(oauth.OAuthProviderError):
        config(redirect=redirect)


@pytest.mark.parametrize(
    "redirect", ["http://localhost:8000/cb", "http://127.0.0.1/cb", "http://[::1]/cb"]
)
def test_explicit_local_callbacks_supported(redirect):
    assert config(redirect=redirect).redirect_uri == redirect


@pytest.mark.parametrize("verifier", [None, "short", "!" * 43, "A" * 129])
def test_github_pkce_required_before_exchange(verifier, no_network):
    with pytest.raises(oauth.OAuthProviderError):
        oauth.exchange_code(config(), code="fixture", code_verifier=verifier)
    no_network.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        {"scope": "repo"},
        {"refresh_token": None},
        {"expires_in": None},
        {"expires_in": True},
        {"access_token": "x\nsecret"},
        {"token_type": "mac"},
    ],
)
def test_invalid_token_response_fails_closed(change, no_network):
    respond(no_network, payload() | change)
    with pytest.raises(oauth.OAuthProviderError):
        oauth.exchange_code(config(), code="fixture", code_verifier="A" * 43)


@pytest.mark.parametrize("status", [301, 302, 401, 429, 500])
def test_http_errors_do_not_leak_provider_body(status, no_network):
    respond(no_network, {"secret": "never-echo-this"}, status)
    with pytest.raises(oauth.OAuthProviderError) as error:
        oauth.exchange_code(config(), code="fixture", code_verifier="A" * 43)
    assert "never-echo-this" not in str(error.value)
    assert error.value.__suppress_context__


def test_transport_exception_redacted(no_network):
    no_network.side_effect = RuntimeError("secret-fixture")
    with pytest.raises(oauth.OAuthProviderError) as error:
        oauth.github_identity("access-fixture")
    assert "fixture" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "raw", [b"not json", b"[]", b"{" + b"x" * oauth.MAX_RESPONSE_BYTES]
)
def test_bad_or_oversized_response_rejected(raw, no_network):
    response = respond(no_network, {})
    response.iter_content.return_value = [raw]
    with pytest.raises(oauth.OAuthProviderError):
        oauth.github_identity("fixture")


def test_identity_safe_projection(no_network):
    respond(
        no_network,
        {"id": 42, "login": "octocat", "email": "private", "access_token": "secret"},
    )
    assert oauth.github_identity("fixture") == {"id": 42, "login": "octocat"}


def installation():
    return {
        "id": 7,
        "account": {"login": "owner"},
        "repository_selection": "selected",
        "permissions": {"issues": "read", "pull_requests": "read", "metadata": "read"},
    }


def test_installation_and_repo_discovery_bounded(no_network):
    respond(no_network, {"installations": [installation()], "total_count": 101})
    result = oauth.github_installations("fixture")
    assert result["incomplete"] is True and result["installations"][0]["id"] == 7
    respond(
        no_network,
        {"repositories": [{"id": 2, "full_name": "Owner/Repo"}], "total_count": 1},
    )
    assert oauth.github_installation_repositories("fixture", 7) == {
        "repositories": [{"id": 2, "full_name": "owner/repo"}],
        "incomplete": False,
    }
    assert (
        no_network.call_args.args[1]
        == "https://api.github.com/user/installations/7/repositories"
    )


@pytest.mark.parametrize(
    "permissions",
    [
        {"issues": "write", "pull_requests": "read"},
        {"issues": "read"},
        {"issues": "read", "pull_requests": "read", "contents": "write"},
    ],
)
def test_installation_broad_permissions_rejected(permissions, no_network):
    respond(
        no_network,
        {
            "installations": [installation() | {"permissions": permissions}],
            "total_count": 1,
        },
    )
    with pytest.raises(oauth.OAuthProviderError):
        oauth.github_installations("fixture")


@pytest.mark.parametrize("identifier", [True, 0, -1, "../../evil", 2**64])
def test_installation_path_is_not_user_url(identifier, no_network):
    with pytest.raises(oauth.OAuthProviderError):
        oauth.github_installation_repositories("fixture", identifier)
    no_network.assert_not_called()


def test_config_repr_redacts_secret():
    assert "secret-fixture" not in repr(config())


def test_classic_oauth_token_not_accepted_as_github_app(no_network):
    respond(no_network, payload() | {"access_token": "gho_classic"})
    with pytest.raises(oauth.OAuthProviderError):
        oauth.exchange_code(config(), code="fixture", code_verifier="A" * 43)


def test_suspended_installation_denied(no_network):
    respond(
        no_network,
        {
            "installations": [installation() | {"suspended_at": "2026-11-13"}],
            "total_count": 1,
        },
    )
    with pytest.raises(oauth.OAuthProviderError):
        oauth.github_installations("fixture")


def test_notion_initial_requires_identity_metadata(no_network):
    respond(no_network, payload("notion") | {"workspace_id": "not-a-uuid"})
    with pytest.raises(oauth.OAuthProviderError):
        oauth.exchange_code(config("notion"), code="fixture")


def test_notion_refresh_can_omit_metadata_but_never_token_rotation(no_network):
    respond(no_network, {"access_token": "new-access", "refresh_token": "new-refresh"})
    assert oauth.refresh_tokens(config("notion"), refresh_token="old").metadata == {}
    respond(no_network, {"access_token": "new-access"})
    with pytest.raises(oauth.OAuthProviderError):
        oauth.refresh_tokens(config("notion"), refresh_token="old")


def test_oversized_discovery_page_denied(no_network):
    respond(no_network, {"installations": [installation()] * 101, "total_count": 101})
    with pytest.raises(oauth.OAuthProviderError):
        oauth.github_installations("fixture")
