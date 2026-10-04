"""Alternate transport for an existing account session in qualified hosted Scout.

Access admission is never an account principal. After validating admission, this
adapter presents the account bytes to the existing canonical Bearer validators.
It does not issue tokens, resolve users, or supply a validation fallback.
"""

from __future__ import annotations

import os
from http.cookies import SimpleCookie

import jwt
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse

from guardian.core import scout_qualification as qualification

ACCOUNT_HEADER = b"x-guardian-account-session"
HOST = "preview.codexify.space"
ISSUER = "https://resonant-constructs.cloudflareaccess.com"
AUDIENCE = "c8cee0fe30547bc752dcbf295fac2a734657668fe6238df8a782e5e9b7bc1b51"
ADMISSION_HEADER = "X-Scout-Access-Admission"
_keys = jwt.PyJWKClient(ISSUER + "/cdn-cgi/access/certs", timeout=5)


def verify_access_assertion(assertion: str) -> None:
    key = _keys.get_signing_key_from_jwt(assertion).key
    jwt.decode(
        assertion,
        key,
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={"require": ["exp", "iat", "iss", "aud"]},
    )


def verify_selected_account(scope) -> None:
    # Reuse canonical purpose, live session mapping and preview eligibility.
    # This also covers handlers such as logout that otherwise only revoke a key.
    from guardian.core.dependencies import verify_account_session

    request = Request(scope)
    verify_account_session(request, None, request.headers.get("Authorization"), None)


def native_authorization_rejection(request: Request) -> str | None:
    """Shape only, never admission: callers must verify qualified signed Access.

    The independently qualified preview edge consumes the native OAuth Bearer.
    Its absence confers no trust. A forwarded header retains the strict old shape.
    """
    values = request.headers.getlist("Authorization")
    if len(values) > 1:
        return "ambiguousAuthorization"
    if values and not values[0].startswith("Bearer oauth:"):
        return "unsupportedAuthorization"
    return None


def admission_headers(request: Request) -> dict[str, str]:
    """Fixed observation only; use after qualified Access validation succeeds."""
    return {
        ADMISSION_HEADER: (
            "opaque-forwarded"
            if request.headers.getlist("Authorization")
            else "edge-consumed"
        )
    }


def account_route(path: str) -> bool:
    """Scope normalization to Scout's existing account APIs and handoff/logout."""
    return path.startswith(
        ("/api/chat/", "/api/tasks/", "/api/threads/", "/api/documents/")
    ) or path in {"/api/media/documents", "/api/auth/logout", "/api/auth/scout/handoff"}


class ScoutAccountTransportMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = scope.get("headers", [])
        account_values = [v for k, v in headers if k.lower() == ACCOUNT_HEADER]
        if not account_values:
            return await self.app(scope, receive, send)

        # Never log header values or exception details: both tokens are sensitive.
        request = Request(scope)
        accepted = (
            len(account_values) == 1
            and os.getenv("GUARDIAN_EXPOSURE_MODE") == "private_preview"
            and request.url.hostname == HOST
            and request.url.port in (None, 443)
            and account_route(scope["path"])
        )
        values = {}
        for name in (b"cf-access-jwt-assertion", b"host"):
            matches = [v for k, v in headers if k.lower() == name]
            accepted = accepted and len(matches) == 1
            values[name] = matches[0] if len(matches) == 1 else b""
        accepted = accepted and native_authorization_rejection(request) is None
        accepted = accepted and not any(
            k.lower() in {b"x-api-key", b"x-guardian-key"} for k, _ in headers
        )
        cookies = SimpleCookie()
        try:
            for name, value in headers:
                if name.lower() == b"cookie":
                    cookies.load(value.decode("latin-1"))
            accepted = accepted and not any(
                name in cookies
                for name in ("gc_session", "codexify_hosted_room_session")
            )
            token = account_values[0].decode("ascii")
            accepted = accepted and 0 < len(token) <= 8192
            accepted = accepted and all(33 <= ord(char) <= 126 for char in token)
            if accepted:
                await run_in_threadpool(
                    verify_access_assertion,
                    values[b"cf-access-jwt-assertion"].decode("ascii"),
                )
        except Exception:
            accepted = False
        if not accepted:
            if scope["path"] == "/api/chat/threads":
                qualification.observe(
                    qualification.request_attempt(request),
                    "protected_read",
                    "failed",
                    400,
                )
            response = JSONResponse(
                {"detail": "Hosted account transport rejected"},
                status_code=400,
                headers={"Cache-Control": "no-store"},
            )
            return await response(scope, receive, send)

        normalized = dict(scope)
        normalized["headers"] = [
            (k, v)
            for k, v in headers
            if k.lower() not in {ACCOUNT_HEADER, b"authorization"}
        ] + [(b"authorization", b"Bearer " + account_values[0])]
        try:
            await run_in_threadpool(verify_selected_account, normalized)
        except HTTPException as exc:
            if scope["path"] == "/api/chat/threads":
                qualification.observe(
                    qualification.request_attempt(request),
                    "protected_read",
                    "failed",
                    exc.status_code,
                )
            response = JSONResponse(
                {"detail": "Account session required"},
                status_code=exc.status_code,
                headers={
                    "Cache-Control": "no-store",
                    **(exc.headers or {}),
                    **admission_headers(request),
                },
            )
            return await response(scope, receive, send)

        # Downstream account validators receive only the selected account
        # session; no alternate credential can retry a failed selection.
        async def qualified_send(message):
            if (
                scope["path"] == "/api/chat/threads"
                and message["type"] == "http.response.start"
            ):
                status = message["status"]
                qualification.observe(
                    qualification.request_attempt(request),
                    "protected_read",
                    "passed" if status == 200 else "failed",
                    status,
                )
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = list(message.get("headers", [])) + [
                    (
                        ADMISSION_HEADER.lower().encode("ascii"),
                        admission_headers(request)[ADMISSION_HEADER].encode("ascii"),
                    )
                ]
            await send(message)

        return await self.app(normalized, receive, qualified_send)
