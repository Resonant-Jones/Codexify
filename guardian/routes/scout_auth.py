"""PKCE-bound issuance of an independent canonical account session for Scout."""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    _verified_session_token_claims,
    issue_session_token,
    resolve_account_session_subject,
)
from guardian.core.auth_dependencies import extract_session_token
from guardian.core.dependencies import verify_account_session
from guardian.core.preview_access import is_private_preview
from guardian.core.scout_account_transport import HOST, verify_access_assertion
from guardian.core.scout_handoff import (
    CALLBACK,
    ORIGIN,
    HandoffUnavailable,
    ScoutHandoffStore,
)
from guardian.core.session_store import DEFAULT_SESSION_TTL_SECONDS, get_session_store

SAFE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class SafeAuthRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request):
            try:
                return await handler(request)
            except RequestValidationError:
                # Default validation errors include input values. Handoff code
                # and verifier must never be echoed in errors or diagnostics.
                return JSONResponse(
                    {"detail": "Invalid handoff request"},
                    status_code=400,
                    headers=SAFE_HEADERS,
                )

        return safe_handler


router = APIRouter(prefix="/api/auth/scout", tags=["Auth"], route_class=SafeAuthRoute)


class CreateHandoff(BaseModel):
    challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$", max_length=43)
    state: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$", max_length=43)
    model_config = ConfigDict(extra="forbid")


class ExchangeHandoff(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$", max_length=43)
    verifier: str = Field(pattern=r"^[A-Za-z0-9._~-]{43,128}$", max_length=128)
    model_config = ConfigDict(extra="forbid")


async def require_hosted_admission(request: Request) -> None:
    if (
        not is_private_preview()
        or request.url.hostname != HOST
        or request.url.port not in (None, 443)
    ):
        raise HTTPException(
            status_code=400,
            detail="Hosted Scout composition required",
            headers=SAFE_HEADERS,
        )
    try:
        if (
            len(request.headers.getlist("Host")) != 1
            or len(request.headers.getlist("Cf-Access-Jwt-Assertion")) != 1
        ):
            raise ValueError("Ambiguous hosted admission")
        await run_in_threadpool(
            verify_access_assertion, request.headers.get("Cf-Access-Jwt-Assertion", "")
        )
    except Exception:
        raise HTTPException(
            status_code=401, detail="Hosted admission required", headers=SAFE_HEADERS
        ) from None


@router.post("/handoff")
async def create_handoff(
    body: CreateHandoff, request: Request, _: None = Depends(require_hosted_admission)
):
    # This is a same-origin browser action after ordinary canonical login, not
    # an Access-identity-to-account exchange or a new session issuer.
    if request.headers.get("Origin") != "https://" + HOST:
        raise HTTPException(
            status_code=400,
            detail="Same-origin browser confirmation required",
            headers=SAFE_HEADERS,
        )
    if (
        len(request.headers.getlist("Authorization")) > 1
        or (
            request.headers.get("Authorization") is not None
            and "gc_session" in request.cookies
        )
        or "codexify_hosted_room_session" in request.cookies
        or "X-API-Key" in request.headers
        or "X-Guardian-Key" in request.headers
    ):
        raise HTTPException(
            status_code=400,
            detail="Conflicting account transports",
            headers=SAFE_HEADERS,
        )
    verify_account_session(
        request,
        None,
        request.headers.get("Authorization"),
        request.cookies.get("gc_session"),
    )
    token = extract_session_token(
        request.headers.get("Authorization"), request.cookies.get("gc_session")
    )
    subject = resolve_account_session_subject(token or "")
    if get_session_store().verify(token) != subject:
        raise HTTPException(
            status_code=401, detail="Account session required", headers=SAFE_HEADERS
        )
    claims = _verified_session_token_claims(token)
    try:
        code = await run_in_threadpool(
            ScoutHandoffStore().create,
            challenge=body.challenge,
            state=body.state,
            token=token,
            user_id=subject,
            expires_at=int(claims["exp"]),
            origin=ORIGIN,
        )
    except HandoffUnavailable:
        raise HTTPException(
            status_code=400, detail="Handoff unavailable", headers=SAFE_HEADERS
        ) from None
    return JSONResponse(
        {"callback": CALLBACK + "?" + urlencode({"code": code, "state": body.state})},
        headers=SAFE_HEADERS,
    )


@router.post("/exchange")
async def exchange_handoff(
    body: ExchangeHandoff, request: Request, _: None = Depends(require_hosted_admission)
):
    if (
        len(request.headers.getlist("Authorization")) != 1
        or not request.headers.get("Authorization", "").startswith("Bearer oauth:")
        or "gc_session" in request.cookies
        or "codexify_hosted_room_session" in request.cookies
        or "X-API-Key" in request.headers
        or "X-Guardian-Key" in request.headers
    ):
        raise HTTPException(
            status_code=400,
            detail="Native Access admission required",
            headers=SAFE_HEADERS,
        )
    try:
        grant = await run_in_threadpool(
            ScoutHandoffStore().consume,
            code=body.code,
            verifier=body.verifier,
            origin=ORIGIN,
        )
        token = grant["token"]
        subject = resolve_account_session_subject(token)
        if subject != grant["user_id"] or get_session_store().verify(token) != subject:
            raise HandoffUnavailable()
        # Reuse the strict canonical purpose, stored-session and preview-account
        # checks, with no fallback to the native ingress credential.
        account_scope = dict(request.scope)
        account_scope["headers"] = [
            (k, v)
            for k, v in request.scope["headers"]
            if k.lower()
            not in {b"authorization", b"cookie", b"x-guardian-account-session"}
        ]
        account_scope["headers"].append(
            (b"authorization", ("Bearer " + token).encode("ascii"))
        )
        verify_account_session(Request(account_scope), None, "Bearer " + token, None)
    except (HandoffUnavailable, HTTPException, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Handoff unavailable; sign in again",
            headers=SAFE_HEADERS,
        ) from None
    # This is the canonical issuer and exact credential class, with a fresh
    # nonce/expiry and independent store entry. The parent browser credential
    # authorizes this one exchange but is never returned to the native client.
    native_token, native_expiry = issue_session_token(
        subject=subject,
        ttl_seconds=DEFAULT_SESSION_TTL_SECONDS,
        purpose=ACCOUNT_SESSION_PURPOSE,
    )
    await run_in_threadpool(
        get_session_store().store,
        native_token,
        subject,
        DEFAULT_SESSION_TTL_SECONDS,
    )
    return JSONResponse(
        {"token": native_token, "user_id": subject, "expires_at": native_expiry},
        headers=SAFE_HEADERS,
    )
