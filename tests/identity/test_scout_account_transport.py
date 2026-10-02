import pytest
from starlette.testclient import TestClient

from guardian.core import scout_account_transport as transport


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setattr(transport, "verify_access_assertion", lambda _: None)

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

    return TestClient(
        transport.ScoutAccountTransportMiddleware(downstream),
        base_url="https://preview.codexify.space",
    )


def headers():
    return {
        "Authorization": "Bearer oauth:fixture-ingress",
        "CF-Access-Jwt-Assertion": "fixture-assertion",
        "X-Guardian-Account-Session": "fixture-account",
    }


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


def test_normalization_preserves_exact_canonical_account_purpose(monkeypatch):
    from fastapi import HTTPException
    from starlette.responses import JSONResponse

    from guardian.core import auth, session_store

    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "synthetic-unit-test-signing-fixture")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setattr(transport, "verify_access_assertion", lambda _: None)

    class Store:
        def verify(self, token):
            return "fixture-user"

    monkeypatch.setattr(session_store, "get_session_store", lambda: Store())

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

    client = TestClient(
        transport.ScoutAccountTransportMiddleware(protected),
        base_url="https://preview.codexify.space",
    )
    for purpose, expected in (
        (auth.ACCOUNT_SESSION_PURPOSE, 200),
        (auth.OPERATOR_SESSION_PURPOSE, 401),
        ("hosted_room_guest_session", 401),
    ):
        token, _ = auth.issue_session_token(subject="fixture-user", purpose=purpose)
        response = client.get(
            "/api/chat/threads",
            headers=headers() | {"X-Guardian-Account-Session": token},
        )
        assert response.status_code == expected
        if expected == 200:
            assert response.json() == {"subject": "fixture-user"}


def test_transport_headers_are_redacted_from_raw_logging():
    from guardian.utils.log_safety import sanitize_log_text

    for name in ("X-Guardian-Account-Session", "Cf-Access-Jwt-Assertion"):
        result = sanitize_log_text(name + ": fixture-sensitive-material")
        assert "fixture-sensitive-material" not in result
