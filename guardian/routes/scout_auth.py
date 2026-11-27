"""PKCE-bound issuance of an independent canonical account session for Scout."""

from urllib.parse import urlencode
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from guardian.core import scout_qualification as qualification
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    _verified_session_token_claims,
    issue_session_token,
    resolve_account_session_subject,
)
from guardian.core.auth_dependencies import extract_session_token
from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import (
    RequestUserScope,
    get_account_user_scope,
    verify_account_session,
)
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
from guardian.db.models import User, UserProfile
from guardian.presentation_tokens import MAX_WALLPAPER_BYTES
from guardian.services import account_presentation

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
                if request.url.path.startswith("/api/auth/scout/profile"):
                    return JSONResponse(
                        {"detail": "Invalid profile request"},
                        status_code=400,
                        headers=SAFE_HEADERS,
                    )
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


def _profile_owner(request: Request, scope: RequestUserScope) -> str:
    token = extract_session_token(
        request.headers.get("Authorization"), request.cookies.get("gc_session")
    )
    if (
        not token
        or not scope.account_id
        or scope.subject_id
        != resolve_account_session_subject(token, require_stored_session=True)
    ):
        raise HTTPException(
            status_code=401, detail="Account session required", headers=SAFE_HEADERS
        )
    return scope.account_id


def _profile_db():
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(
            status_code=503, detail="Profile unavailable", headers=SAFE_HEADERS
        )
    return db


def _profile_payload(greeting_name=None):
    return {
        "greeting_name": (greeting_name or "").strip() or None,
    }


@router.get("/profile", include_in_schema=False)
def read_scout_profile(
    request: Request, scope: RequestUserScope = Depends(get_account_user_scope)
) -> JSONResponse:
    """Read authored presentation; only an explicitly saved name is a greeting."""
    owner = _profile_owner(request, scope)
    try:
        with _profile_db().get_session() as session:
            greeting_name = session.execute(
                select(UserProfile.greeting_name).where(UserProfile.user_id == owner)
            ).scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503, detail="Profile unavailable", headers=SAFE_HEADERS
        ) from None
    return JSONResponse(_profile_payload(greeting_name), headers=SAFE_HEADERS)


class GreetingNameUpdate(BaseModel):
    greeting_name: str | None = Field(max_length=255, strict=True)
    model_config = ConfigDict(extra="forbid")

    @field_validator("greeting_name")
    @classmethod
    def normalize_name(cls, value):
        value = value.strip() if value is not None else None
        if not value:
            return None
        if any(
            ord(char) < 32 or ord(char) == 127 or char in "\x85\u2028\u2029"
            for char in value
        ):
            raise ValueError("Greeting name must be a single line")
        return value


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


@router.patch("/profile", include_in_schema=False)
def save_greeting_name(
    request: Request,
    body: GreetingNameUpdate,
    scope: RequestUserScope = Depends(get_account_user_scope),
    _: None = Depends(require_hosted_admission),
) -> JSONResponse:
    """Save or clear only the authenticated owner's explicit greeting choice."""
    owner = _profile_owner(request, scope)
    if (
        len(request.headers.getlist("Authorization")) > 1
        or any(name in request.headers for name in ("X-API-Key", "X-Guardian-Key"))
        or "codexify_hosted_room_session" in request.cookies
        or ("Authorization" in request.headers and "gc_session" in request.cookies)
    ):
        raise HTTPException(
            status_code=400,
            detail="Conflicting account transports",
            headers=SAFE_HEADERS,
        )
    if "gc_session" in request.cookies and request.headers.get("Origin") != ORIGIN:
        raise HTTPException(
            status_code=403, detail="Same-origin save required", headers=SAFE_HEADERS
        )
    try:
        with _profile_db().get_session() as session:
            # Lock the canonical account to serialize first-profile creation.
            user = session.scalar(
                select(User.id).where(User.id == owner).with_for_update()
            )
            if user is None:
                raise HTTPException(
                    status_code=404, detail="User unavailable", headers=SAFE_HEADERS
                )
            profile = session.scalar(
                select(UserProfile).where(UserProfile.user_id == owner)
            )
            if profile is None:
                profile = UserProfile(user_id=owner, greeting_name=body.greeting_name)
                session.add(profile)
            else:
                profile.greeting_name = body.greeting_name
            session.flush()
            payload = _profile_payload(profile.greeting_name)
            session.commit()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503, detail="Profile unavailable", headers=SAFE_HEADERS
        ) from None
    return JSONResponse(payload, headers=SAFE_HEADERS)


class AppearancePatch(BaseModel):
    theme_mode: Literal["system", "light", "dark"] | None = None
    base_color: str | None = Field(
        default=None, pattern=r"^#[0-9A-Fa-f]{6}$", strict=True
    )
    background_depth: float | None = Field(default=None, ge=0, le=1, strict=True)
    background_fade: float | None = Field(default=None, ge=0, le=1, strict=True)
    surface_depth: int | None = Field(default=None, ge=0, le=100, strict=True)
    surface_warmth: int | None = Field(default=None, ge=-100, le=100, strict=True)
    glass_treatment: Literal["refractive", "frosted", "solid"] | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def explicit_values(self):
        if not self.model_fields_set or any(
            getattr(self, k) is None for k in self.model_fields_set
        ):
            raise ValueError("Provide appearance values")
        return self


class PresentationUpdate(BaseModel):
    workspace_id: UUID
    settings: AppearancePatch | None = None
    workspace_unique: StrictBool | None = None
    clear_wallpaper: StrictBool | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def single_intent(self):
        if self.clear_wallpaper is False:
            raise ValueError("Clear wallpaper must be explicit")
        if self.workspace_unique is not None:
            if self.settings is not None or self.clear_wallpaper is not None:
                raise ValueError("Save workspace mode separately")
        elif self.settings is None and self.clear_wallpaper is None:
            raise ValueError("Provide an appearance change")
        return self


def presentation_write_owner(request, scope):
    owner = _profile_owner(request, scope)
    if (
        len(request.headers.getlist("Authorization")) > 1
        or any(k in request.headers for k in ("X-API-Key", "X-Guardian-Key"))
        or "codexify_hosted_room_session" in request.cookies
        or ("Authorization" in request.headers and "gc_session" in request.cookies)
    ):
        raise HTTPException(400, "Conflicting account transports", headers=SAFE_HEADERS)
    if "gc_session" in request.cookies and request.headers.get("Origin") != ORIGIN:
        raise HTTPException(403, "Same-origin save required", headers=SAFE_HEADERS)
    return owner


def presentation_call(request, scope, action, *, write=False):
    owner = (
        presentation_write_owner(request, scope)
        if write
        else _profile_owner(request, scope)
    )
    try:
        with _profile_db().get_session() as session:
            result = action(session, owner)
            if write:
                session.commit()
            return result
    except SQLAlchemyError:
        raise HTTPException(
            503, "Appearance unavailable", headers=SAFE_HEADERS
        ) from None


@router.get("/profile/presentation", include_in_schema=False)
def read_presentation(
    workspace_id: UUID,
    request: Request,
    scope: RequestUserScope = Depends(get_account_user_scope),
    _: None = Depends(require_hosted_admission),
):
    data = presentation_call(
        request,
        scope,
        lambda session, owner: account_presentation.payload(
            session, owner, workspace_id
        ),
    )
    return JSONResponse(data, headers=SAFE_HEADERS)


@router.patch("/profile/presentation", include_in_schema=False)
def save_presentation(
    body: PresentationUpdate,
    request: Request,
    scope: RequestUserScope = Depends(get_account_user_scope),
    _: None = Depends(require_hosted_admission),
):
    data = presentation_call(
        request,
        scope,
        lambda session, owner: account_presentation.save(
            session,
            owner,
            body.workspace_id,
            settings=(
                body.settings.model_dump(exclude_unset=True) if body.settings else None
            ),
            unique=body.workspace_unique,
            clear_wallpaper=bool(body.clear_wallpaper),
        ),
        write=True,
    )
    return JSONResponse(data, headers=SAFE_HEADERS)


@router.get("/profile/presentation/wallpaper", include_in_schema=False)
def read_presentation_wallpaper(
    workspace_id: UUID,
    request: Request,
    scope: RequestUserScope = Depends(get_account_user_scope),
    _: None = Depends(require_hosted_admission),
):
    data, mime = presentation_call(
        request,
        scope,
        lambda session, owner: account_presentation.wallpaper(
            session, owner, workspace_id
        ),
    )
    return Response(
        data,
        media_type=mime,
        headers={**SAFE_HEADERS, "X-Content-Type-Options": "nosniff"},
    )


@router.put("/profile/presentation/wallpaper", include_in_schema=False)
async def save_presentation_wallpaper(
    workspace_id: UUID,
    request: Request,
    scope: RequestUserScope = Depends(get_account_user_scope),
    _: None = Depends(require_hosted_admission),
):
    # Authenticate before consuming the body, then bound even chunked uploads.
    presentation_write_owner(request, scope)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_WALLPAPER_BYTES:
            raise HTTPException(
                413, "Wallpaper must be at most 5 MB", headers=SAFE_HEADERS
            )
        data.extend(chunk)
    result = await run_in_threadpool(
        presentation_call,
        request,
        scope,
        lambda session, owner: account_presentation.upload(
            session, owner, workspace_id, bytes(data)
        ),
        write=True,
    )
    return JSONResponse(result, headers=SAFE_HEADERS)


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
