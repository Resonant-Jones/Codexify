"""Browser OAuth setup routes, isolated from connector read/worker authority."""

from __future__ import annotations

import secrets
from typing import Any, Callable
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from guardian.connections import (
    knowledge_oauth as oauth,
    oauth_store as store,
    oauth_providers as providers,
)
from guardian.connections.credential_routes import CredentialSetupRoute
from guardian.core.dependencies import get_account_user_id, require_account_session


class RepositorySelection(BaseModel):
    installation_id: int = Field(gt=0)
    repositories: list[str] = Field(min_length=1, max_length=20)


def _failure() -> HTTPException:
    return HTTPException(409, detail={"error": "knowledge_oauth_action_failed"})


def make_router(provider: str, get_db: Callable[[], Any]) -> APIRouter:
    name = "notion" if provider == "notion" else "github-knowledge"
    prefix = f"/api/connect/{name}/oauth"
    cookie_name = f"codexify_oauth_{provider}"
    router = APIRouter(prefix=prefix, route_class=CredentialSetupRoute)
    auth = [Depends(require_account_session)]

    def ensure_origin(request: Request) -> None:
        # A configured callback is the authority for browser origin. Without
        # provider config, same-origin account UI can still disconnect locally.
        try:
            parsed = urlsplit(oauth.config(provider).redirect_uri)
        except oauth.KnowledgeOAuthError:
            parsed = urlsplit(str(request.base_url))
        expected = f"{parsed.scheme}://{parsed.netloc}"
        # Browser starts are same-origin, not caller-specified redirect targets.
        if request.headers.get("origin") != expected:
            raise HTTPException(403, detail={"error": "knowledge_oauth_origin_denied"})

    @router.post("/start", dependencies=auth)
    def start(
        request: Request,
        response: Response,
        user_id: str = Depends(get_account_user_id),
    ):
        try:
            ensure_origin(request)
            binding = secrets.token_urlsafe(32)
            result = oauth.begin(get_db(), user_id, provider, binding)
            cfg = oauth.config(provider)
            response.set_cookie(
                cookie_name,
                binding,
                max_age=600,
                httponly=True,
                secure=urlsplit(cfg.redirect_uri).scheme == "https",
                samesite="lax",
                path=prefix,
            )
            response.headers["Cache-Control"] = "no-store"
            return result
        except HTTPException:
            raise
        except Exception:
            raise _failure() from None

    @router.get("/callback", response_class=HTMLResponse)
    def callback(
        request: Request,
        state: str = "",
        code: str | None = None,
        error: str | None = None,
    ):
        # No query values, provider messages, codes or identities are reflected.
        try:
            binding = request.cookies.get(cookie_name, "")
            if not binding:
                raise ValueError()
            oauth.complete(get_db(), provider, state, code, error, binding)
            message = "Authorization complete. Return to Codexify to finish setup."
            status_code = 200
        except Exception:
            message = (
                "Authorization could not complete. Return to Codexify and reconnect."
            )
            status_code = 400
        response = HTMLResponse(
            f"<!doctype html><title>Codexify connection</title><p>{message}</p>",
            status_code=status_code,
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            },
        )
        response.delete_cookie(cookie_name, path=prefix)
        return response

    @router.get("/status", dependencies=auth)
    def status(response: Response, user_id: str = Depends(get_account_user_id)):
        response.headers["Cache-Control"] = "no-store"
        try:
            return oauth.status(get_db(), user_id, provider)
        except Exception:
            raise _failure() from None

    @router.post("/disconnect", dependencies=auth)
    def disconnect(request: Request, user_id: str = Depends(get_account_user_id)):
        # Existing account auth is still required when provider config was removed.
        try:
            ensure_origin(request)
            db = get_db()
            removed = store.disconnect(db, user_id, provider)
            # Clear legacy credential too: disabling OAuth cannot resurrect it.
            from guardian.connections.github import credentials as github_credentials
            from guardian.connections.notion import credentials as notion_credentials

            legacy = github_credentials if provider == "github" else notion_credentials
            removed = legacy.disconnect(db, user_id) or removed
            return {"removed": removed, "provider_revoked": False}
        except Exception:
            raise _failure() from None

    if provider == "github":

        def token(user_id: str):
            snapshot = oauth.credential(get_db(), user_id, provider)
            if snapshot is None:
                raise ValueError()
            return snapshot.access_token

        @router.get("/installations", dependencies=auth)
        def installations(user_id: str = Depends(get_account_user_id)):
            try:
                return providers.github_installations(token(user_id))
            except Exception:
                raise _failure() from None

        @router.get("/installations/{installation_id}/repositories", dependencies=auth)
        def repositories(
            installation_id: int, user_id: str = Depends(get_account_user_id)
        ):
            try:
                access_token = token(user_id)
                installs = providers.github_installations(access_token)["installations"]
                if installation_id not in {entry["id"] for entry in installs}:
                    raise ValueError()
                return providers.github_installation_repositories(
                    access_token, installation_id
                )
            except Exception:
                raise _failure() from None

        @router.put("/repositories", dependencies=auth)
        def select(
            payload: RepositorySelection,
            request: Request,
            user_id: str = Depends(get_account_user_id),
        ):
            try:
                ensure_origin(request)
                oauth.select_repositories(
                    get_db(), user_id, payload.installation_id, payload.repositories
                )
                return oauth.status(get_db(), user_id, provider)
            except Exception:
                raise _failure() from None

    return router
