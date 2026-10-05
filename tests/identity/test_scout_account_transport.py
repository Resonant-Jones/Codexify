import pytest
from starlette.testclient import TestClient

from guardian.core import scout_account_transport as transport


@pytest.mark.parametrize(
    "header", ["X-Guardian-Account-Session", "Cf-Access-Jwt-Assertion"]
)
def test_hosted_credential_assignments_are_redacted_from_logs(header):
    import logging

    from guardian.utils.log_safety import sanitize_record

    marker = "synthetic-hosted-credential-never-log"
    record = logging.LogRecord(
        "scout-fixture", logging.WARNING, __file__, 1, f"{header}={marker}", (), None
    )
    sanitized = sanitize_record(record, force=True)
    assert marker not in sanitized.getMessage()


@pytest.mark.parametrize(
    "field", ["x_guardian_account_session", "cf_access_jwt_assertion"]
)
def test_structured_hosted_credentials_are_redacted_from_logs(field):
    import logging

    from guardian.utils.log_safety import sanitize_record

    marker = "synthetic-hosted-credential-never-log"
    record = logging.LogRecord(
        "scout-fixture", logging.WARNING, __file__, 1, "event", (), None
    )
    setattr(record, field, marker)
    sanitized = sanitize_record(record, force=True)
    assert marker not in str(getattr(sanitized, field))


def _scout_client(*args, **kwargs):
    client = TestClient(*args, **kwargs)
    # The repository bootstrap injects an operator key by default. Scout tests
    # must exercise only the credential selectors explicitly supplied per call.
    client.headers.pop("X-API-Key", None)
    return client


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setattr(transport, "verify_access_assertion", lambda _: None)

    monkeypatch.setattr(transport, "verify_selected_account", lambda _: None)

    async def downstream(scope, receive, send):
        from starlette.responses import JSONResponse

        headers = dict(scope["headers"])
        # Synthetic fixture bytes only, never production credential inspection.
        response = JSONResponse(
            {
                "selected": headers.get(b"authorization", b"").decode(),
                "alternate_removed": transport.ACCOUNT_HEADER not in headers,
            }
        )
        await response(scope, receive, send)

    return _scout_client(
        transport.ScoutAccountTransportMiddleware(downstream),
        base_url="https://preview.codexify.space",
    )


def headers():
    return {
        "Authorization": "Bearer oauth:fixture-ingress",
        "CF-Access-Jwt-Assertion": "fixture-assertion",
        "X-Guardian-Account-Session": "fixture-account",
    }


def edge_headers():
    return {name: value for name, value in headers().items() if name != "Authorization"}


def test_edge_consumed_composition_still_requires_selected_account(client):
    response = client.get("/api/chat/threads", headers=edge_headers())
    assert response.status_code == 200
    assert response.headers["X-Scout-Access-Admission"] == "edge-consumed"
    assert response.json()["selected"] == "Bearer fixture-account"
    assert response.json()["alternate_removed"]


@pytest.mark.parametrize(
    "extra",
    [
        {"Host": "personal.example"},
        {"Host": "preview.codexify.space:8443"},
        {"Authorization": "Bearer fixture-account"},
        {"Authorization": ""},
        {"Cookie": "gc_session=fixture-cookie"},
        {"Cookie": "gc_session=fixture-cookie; bad"},
        {"Cookie": "unrelated=value; codexify_hosted_room_session=fixture-guest; bad"},
        {"Cookie": "codexify_hosted_room_session=fixture-guest"},
        {"X-API-Key": "fixture-key"},
        {"X-Guardian-Key": "fixture-key"},
        {"X-Guardian-Account-Session": ""},
    ],
)
def test_edge_consumed_wrong_or_conflicting_composition_rejected(client, extra):
    assert (
        client.get("/api/chat/threads", headers=edge_headers() | extra).status_code
        == 400
    )


def test_edge_consumed_missing_duplicate_invalid_assertion_and_local_mode_rejected(
    client, monkeypatch
):
    absent = {
        name: value
        for name, value in edge_headers().items()
        if name != "CF-Access-Jwt-Assertion"
    }
    assert client.get("/api/chat/threads", headers=absent).status_code == 400
    for name in ["CF-Access-Jwt-Assertion", "Host", "X-Guardian-Account-Session"]:
        pairs = list(edge_headers().items())
        if name == "Host":
            pairs.append(("Host", transport.HOST))
        pairs.append((name, "fixture-duplicate"))
        assert client.get("/api/chat/threads", headers=pairs).status_code == 400
    monkeypatch.setattr(
        transport,
        "verify_access_assertion",
        lambda _: (_ for _ in ()).throw(ValueError()),
    )
    assert client.get("/api/chat/threads", headers=edge_headers()).status_code == 400
    monkeypatch.setattr(transport, "verify_access_assertion", lambda _: None)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local")
    assert client.get("/api/chat/threads", headers=edge_headers()).status_code == 400


def test_edge_consumed_invalid_account_never_falls_back_or_reaches_logout(
    client, monkeypatch
):
    from fastapi import HTTPException

    seen = []

    def invalid(scope):
        seen.append(dict(scope["headers"])[b"authorization"])
        raise HTTPException(status_code=401)

    monkeypatch.setattr(transport, "verify_selected_account", invalid)
    for path in ["/api/chat/threads", "/api/auth/logout"]:
        response = client.post(path, headers=edge_headers())
        assert response.status_code == 401
        assert "selected" not in response.json()
    assert seen == [b"Bearer fixture-account", b"Bearer fixture-account"]


def test_qualified_composition_normalizes_only_account_transport(client):
    response = client.get("/api/chat/threads", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "selected": "Bearer fixture-account",
        "alternate_removed": True,
    }


@pytest.mark.parametrize(
    "path",
    ["/api/admin/session", "/api/operators/continuity", "/health", "/api/auth/login"],
)
def test_other_surfaces_reject_header(client, path):
    assert client.get(path, headers=headers()).status_code == 400


@pytest.mark.parametrize(
    "extra",
    [
        {"Host": "personal.example"},
        {"Authorization": "Bearer fixture-account"},
        {"Cookie": "gc_session=fixture-cookie"},
        {"Cookie": "gc_session=fixture-cookie; bad"},
        {"Cookie": "unrelated=value; codexify_hosted_room_session=fixture-guest; bad"},
        {"Cookie": "codexify_hosted_room_session=fixture-guest"},
        {"X-API-Key": "fixture-key"},
        {"X-Guardian-Key": "fixture-key"},
        {"X-Guardian-Account-Session": ""},
    ],
)
def test_wrong_composition_and_mixed_credentials_fail_closed(client, extra):
    assert client.get("/api/chat/threads", headers=headers() | extra).status_code == 400


def test_unqualified_environment_and_assertion_fail_closed(client, monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local")
    assert client.get("/api/chat/threads", headers=headers()).status_code == 400
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")

    def invalid(_):
        raise ValueError("synthetic invalid assertion")

    monkeypatch.setattr(transport, "verify_access_assertion", invalid)
    assert client.get("/api/chat/threads", headers=headers()).status_code == 400


def test_no_alternate_header_preserves_existing_bearer(client):
    response = client.get(
        "/api/chat/threads", headers={"Authorization": "Bearer fixture-personal"}
    )
    assert response.json()["selected"] == "Bearer fixture-personal"


def test_duplicate_account_or_ingress_headers_rejected(client):
    for name in (
        "X-Guardian-Account-Session",
        "Authorization",
        "CF-Access-Jwt-Assertion",
    ):
        pairs = list(headers().items()) + [(name, "fixture-duplicate")]
        assert client.get("/api/chat/threads", headers=pairs).status_code == 400


def test_assertion_checks_signature_issuer_audience_and_expiry(monkeypatch):
    import time
    from types import SimpleNamespace

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        transport._keys,
        "get_signing_key_from_jwt",
        lambda _: SimpleNamespace(key=key.public_key()),
    )
    claims = {
        "iss": transport.ISSUER,
        "aud": [transport.AUDIENCE],
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
    }
    transport.verify_access_assertion(jwt.encode(claims, key, algorithm="RS256"))
    for changed in (
        claims | {"aud": ["other-application"]},
        claims | {"iss": "https://other.example"},
        claims | {"exp": int(time.time()) - 60},
        {k: v for k, v in claims.items() if k != "exp"},
    ):
        with pytest.raises(jwt.InvalidTokenError):
            transport.verify_access_assertion(
                jwt.encode(changed, key, algorithm="RS256")
            )
    with pytest.raises(jwt.InvalidSignatureError):
        transport.verify_access_assertion(jwt.encode(claims, other, algorithm="RS256"))


@pytest.mark.parametrize("edge_consumed", [False, True])
def test_normalization_preserves_exact_canonical_account_purpose(
    monkeypatch, edge_consumed
):
    from fastapi import HTTPException
    from starlette.responses import JSONResponse

    from guardian.core import auth, session_store

    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "synthetic-unit-test-signing-fixture")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "fixture@example.com")
    monkeypatch.setattr(transport, "verify_access_assertion", lambda _: None)

    class Store:
        def verify(self, token):
            return "fixture@example.com"

    monkeypatch.setattr(session_store, "_SESSION_STORE", Store())

    async def protected(scope, receive, send):
        token = dict(scope["headers"])[b"authorization"].decode()[7:]
        try:
            subject = auth.resolve_account_session_subject(token)
            response = JSONResponse({"subject": subject})
        except HTTPException as exc:
            response = JSONResponse(
                {"detail": "Account session required"}, status_code=exc.status_code
            )
        await response(scope, receive, send)

    client = _scout_client(
        transport.ScoutAccountTransportMiddleware(protected),
        base_url="https://preview.codexify.space",
    )
    for purpose, expected in (
        (auth.ACCOUNT_SESSION_PURPOSE, 200),
        (auth.OPERATOR_SESSION_PURPOSE, 401),
        ("hosted_room_guest_session", 401),
    ):
        token, _ = auth.issue_session_token(
            subject="fixture@example.com", purpose=purpose
        )
        response = client.get(
            "/api/chat/threads",
            headers=(edge_headers() if edge_consumed else headers())
            | {"X-Guardian-Account-Session": token},
        )
        assert response.status_code == expected
        if expected == 200:
            assert response.json() == {"subject": "fixture@example.com"}


def test_transport_headers_are_redacted_from_raw_logging():
    from guardian.utils.log_safety import sanitize_log_text

    for name in ("X-Guardian-Account-Session", "Cf-Access-Jwt-Assertion"):
        result = sanitize_log_text(name + ": fixture-sensitive-material")
        assert "fixture-sensitive-material" not in result


def test_invalid_selected_account_never_reaches_downstream_even_on_logout(
    client, monkeypatch
):
    from fastapi import HTTPException

    def invalid(_):
        raise HTTPException(status_code=401, detail="Account session required")

    monkeypatch.setattr(transport, "verify_selected_account", invalid)
    for path in ["/api/chat/threads", "/api/auth/logout"]:
        response = client.post(path, headers=headers())
        assert response.status_code == 401
        assert "selected" not in response.json()


def test_malformed_duplicate_cookie_headers_cannot_hide_account_selector(client):
    supplied = list(edge_headers().items()) + [
        ("Cookie", "gc_session=fixture-cookie"),
        ("Cookie", "bad"),
    ]
    assert client.get("/api/chat/threads", headers=supplied).status_code == 400
