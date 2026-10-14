"""PKCE-bound issuance of an independent canonical account session for Scout."""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from guardian.core import scout_qualification as qualification
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    _verified_session_token_claims,
    issue_session_token,
    resolve_account_session_subject,
)
from guardian.core.auth_dependencies import extract_session_token
from guardian.core.dependencies import verify_account_session
from guardian.core.preview_access import is_private_preview
from guardian.core.scout_account_transport import (
    HOST,
    admission_headers,
    native_authorization_rejection,
    verify_access_assertion,
)
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
            except HTTPException as exc:
                identity = qualification.request_attempt(request)
                stage = {
                    "/api/auth/scout/handoff": "handoff_redirect",
                    "/api/auth/scout/exchange": "handoff_exchange",
                }.get(request.url.path)
                if stage:
                    qualification.observe(identity, stage, "failed", exc.status_code)
                raise
            except RequestValidationError:
                stage = {
                    "/api/auth/scout/handoff": "handoff_redirect",
                    "/api/auth/scout/exchange": "handoff_exchange",
                }.get(request.url.path)
                if stage:
                    qualification.observe(
                        qualification.request_attempt(request), stage, "failed", 400
                    )
                # Default validation errors include input values. Handoff code
                # and verifier must never be echoed in errors or diagnostics.
                return JSONResponse(
                    {"detail": "Invalid handoff request"},
                    status_code=400,
                    headers=SAFE_HEADERS,
                )
            except Exception:
                identity = qualification.request_attempt(request)
                stage = {
                    "/api/auth/scout/handoff": "handoff_redirect",
                    "/api/auth/scout/exchange": "handoff_exchange",
                }.get(request.url.path)
                evidence = qualification.snapshot(identity)
                if (
                    stage == "handoff_exchange"
                    and evidence
                    and evidence["stages"].get(stage, {}).get("status") == "passed"
                ):
                    stage = "native_session"
                if stage:
                    qualification.observe(identity, stage, "failed", 500)
                # Do not log exception text/body. Existing server error handling
                # and canonical auth semantics remain authoritative.
                raise

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


async def require_native_qualification(request: Request):
    await require_hosted_admission(request)
    # Fixed shape classifications only; never retain or reflect header values.
    reason = native_authorization_rejection(request)
    if reason is None and (
        any(
            name in request.headers
            for name in ("X-Guardian-Account-Session", "X-API-Key", "X-Guardian-Key")
        )
        or any(
            name in request.cookies
            for name in ("gc_session", "codexify_hosted_room_session")
        )
    ):
        reason = "conflictingSelectors"
    if reason:
        raise HTTPException(
            status_code=400,
            detail="Native admission required",
            headers={**SAFE_HEADERS, "X-Scout-Qualification-Rejection": reason},
        )


def require_qualification_id(identity):
    if not qualification.attempt_id(identity):
        raise HTTPException(
            status_code=400,
            detail="Invalid qualification identifier",
            headers=SAFE_HEADERS,
        )


@router.put("/qualification/{identity}")
async def begin_qualification(
    identity: str, request: Request, _: None = Depends(require_native_qualification)
):
    require_qualification_id(identity)
    if not qualification.begin(identity):
        raise HTTPException(
            status_code=503,
            detail="Qualification capacity unavailable",
            headers=SAFE_HEADERS,
        )
    return JSONResponse(
        qualification.snapshot(identity),
        headers={**SAFE_HEADERS, **admission_headers(request)},
    )


@router.get("/qualification/{identity}")
async def read_qualification(
    identity: str, request: Request, _: None = Depends(require_native_qualification)
):
    require_qualification_id(identity)
    evidence = qualification.snapshot(identity)
    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail="Qualification evidence unavailable",
            headers=SAFE_HEADERS,
        )
    return JSONResponse(
        evidence, headers={**SAFE_HEADERS, **admission_headers(request)}
    )


class BrowserObservation(BaseModel):
    event: str = Field(pattern=r"^(loaded|account_confirmed|redirect_dispatched)$")
    model_config = ConfigDict(extra="forbid")


@router.post("/qualification/{identity}/browser")
async def browser_qualification(
    identity: str,
    body: BrowserObservation,
    request: Request,
    _: None = Depends(require_hosted_admission),
):
    require_qualification_id(identity)
    if request.headers.get("Origin") != ORIGIN:
        raise HTTPException(
            status_code=400,
            detail="Same-origin observation required",
            headers=SAFE_HEADERS,
        )
    if body.event != "loaded":
        # Browser UI readiness is not account authority. Confirm with the exact
        # same canonical account validator as the existing handoff.
        if (
            (
                request.headers.get("Authorization") is not None
                and "gc_session" in request.cookies
            )
            or len(request.headers.getlist("Authorization")) > 1
            or any(name in request.headers for name in ("X-API-Key", "X-Guardian-Key"))
            or "codexify_hosted_room_session" in request.cookies
        ):
            raise HTTPException(
                status_code=400,
                detail="Conflicting account transports",
                headers=SAFE_HEADERS,
            )
        try:
            verify_account_session(
                request,
                None,
                request.headers.get("Authorization"),
                request.cookies.get("gc_session"),
            )
        except HTTPException as exc:
            qualification.observe(identity, "account_login", "failed", exc.status_code)
            raise
        qualification.observe(identity, "account_login", "passed", 200)
    if body.event == "loaded":
        qualification.observe(identity, "browser_loaded", "passed", 200)
    return JSONResponse({"ok": True}, headers=SAFE_HEADERS)


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
    qualification.observe(
        qualification.request_attempt(request), "account_login", "passed", 200
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
    qualification.observe(
        qualification.request_attempt(request), "handoff_redirect", "passed", 200
    )
    return JSONResponse(
        {"callback": CALLBACK + "?" + urlencode({"code": code, "state": body.state})},
        headers=SAFE_HEADERS,
    )


@router.post("/exchange")
async def exchange_handoff(
    body: ExchangeHandoff,
    request: Request,
    _: None = Depends(require_native_qualification),
):
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
    qualification.observe(
        qualification.request_attempt(request), "handoff_exchange", "passed", 200
    )
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
    qualification.observe(
        qualification.request_attempt(request), "native_session", "passed", 200
    )
    return JSONResponse(
        {"token": native_token, "user_id": subject, "expires_at": native_expiry},
        headers={
            **SAFE_HEADERS,
            **admission_headers(request),
            "X-Scout-Native-Session-Issued": "true",
        },
    )
