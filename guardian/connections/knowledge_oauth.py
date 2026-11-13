"""Opt-in account-owned OAuth orchestration, not worker execution authority."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import time
from urllib.parse import urlsplit
from typing import Any

from guardian.connections import oauth_providers as providers, oauth_store as store


class KnowledgeOAuthError(RuntimeError):
    """Only bounded public error codes cross the HTTP boundary."""


def enabled() -> bool:
    return os.getenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def config(provider: str) -> providers.OAuthConfig:
    if not enabled() or provider not in {"notion", "github"}:
        raise KnowledgeOAuthError("knowledge_oauth_unavailable")
    prefix = (
        "CODEXIFY_NOTION_OAUTH" if provider == "notion" else "CODEXIFY_GITHUB_APP_OAUTH"
    )
    try:
        result = providers.OAuthConfig(
            provider,
            os.getenv(prefix + "_CLIENT_ID", ""),
            os.getenv(prefix + "_CLIENT_SECRET", ""),
            os.getenv(prefix + "_REDIRECT_URI", ""),
        )
        path = "notion" if provider == "notion" else "github-knowledge"
        if urlsplit(result.redirect_uri).path != f"/api/connect/{path}/oauth/callback":
            raise ValueError()
        return result
    except (ValueError, providers.OAuthProviderError):
        raise KnowledgeOAuthError("knowledge_oauth_operator_setup_required") from None


def eligible(db: Any, user_id: str) -> None:
    from guardian.db.models import User
    from guardian.core.preview_access import is_private_preview, role_for_preview_email

    with db.get_session() as session:
        user = session.query(User).filter_by(id=user_id).one_or_none()
        if user is None or (
            is_private_preview() and not role_for_preview_email(user.email or user.id)
        ):
            raise KnowledgeOAuthError("knowledge_oauth_account_unavailable")


def status(db: Any, user_id: str, provider: str) -> dict[str, Any]:
    result = store.status(db, user_id, provider)
    try:
        config(provider)
        available = True
    except KnowledgeOAuthError:
        available = False
    slug = os.getenv("CODEXIFY_GITHUB_APP_SLUG", "")
    installation_url = (
        f"https://github.com/apps/{slug}/installations/new"
        if provider == "github" and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", slug)
        else None
    )
    return {**result, "available": available, "installation_url": installation_url}


def begin(db: Any, user_id: str, provider: str, browser_binding: str) -> dict[str, Any]:
    cfg = config(provider)
    eligible(db, user_id)
    flow = store.begin_flow(
        db, user_id, provider, cfg.redirect_uri, browser_binding=browser_binding
    )
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(flow.code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    return {
        "authorization_url": providers.authorization_url(
            cfg,
            state=flow.state,
            code_challenge=challenge if provider == "github" else None,
        ),
        "generation": flow.generation,
    }


def complete(
    db: Any,
    provider: str,
    state: str,
    code: str | None,
    error: str | None,
    browser_binding: str,
) -> None:
    cfg = config(provider)
    flow = store.consume_flow(db, provider, state, browser_binding=browser_binding)
    eligible(db, flow.user_id)
    if error or not code or len(code) > 8192 or flow.redirect_uri != cfg.redirect_uri:
        raise KnowledgeOAuthError("knowledge_oauth_authorization_incomplete")
    tokens = providers.exchange_code(
        cfg,
        code=code,
        code_verifier=flow.code_verifier if provider == "github" else None,
    )
    metadata = dict(tokens.metadata)
    if provider == "github":
        metadata.update(providers.github_identity(tokens.access_token))
    else:
        from guardian.connections.notion.service import NotionClient

        NotionClient(tokens.access_token).validate()
    eligible(db, flow.user_id)
    if not store.complete_flow(
        db, flow, tokens.access_token, tokens.refresh_token, tokens.expires_in, metadata
    ):
        raise KnowledgeOAuthError("knowledge_oauth_flow_superseded")


def credential(db: Any, user_id: str, provider: str) -> store.CredentialSnapshot | None:
    eligible(db, user_id)
    snapshot = store.credential(db, user_id, provider)
    if snapshot is None:
        return None
    if snapshot.expires_at is None or snapshot.expires_at > time.time() + 60:
        return snapshot
    claim = store.claim_refresh(db, user_id, provider)
    if claim is None:
        return None
    try:
        tokens = providers.refresh_tokens(
            config(provider), refresh_token=claim.credential.refresh_token or ""
        )
        metadata = dict(claim.credential.metadata)
        if provider == "github":
            identity = providers.github_identity(tokens.access_token)
            if identity.get("id") != metadata.get("id"):
                raise KnowledgeOAuthError("knowledge_oauth_identity_changed")
            metadata.update(identity)
        else:
            for identity_key in ("workspace_id", "bot_id"):
                if tokens.metadata.get(
                    identity_key, metadata.get(identity_key)
                ) != metadata.get(identity_key):
                    raise KnowledgeOAuthError("knowledge_oauth_identity_changed")
            metadata.update(tokens.metadata)
        eligible(db, user_id)
        if not store.complete_refresh(
            db,
            claim,
            tokens.access_token,
            tokens.refresh_token,
            tokens.expires_in,
            metadata,
        ):
            return None
    except Exception:
        store.fail_refresh(db, claim)
        raise KnowledgeOAuthError("knowledge_oauth_reconnect_required") from None
    return store.credential(db, user_id, provider)


def select_repositories(
    db: Any, user_id: str, installation_id: int, repositories: list[str]
) -> None:
    from guardian.connections.github.service import normalize_repository

    snapshot = credential(db, user_id, "github")
    if snapshot is None:
        raise KnowledgeOAuthError("knowledge_oauth_reconnect_required")
    selected = list(
        dict.fromkeys(normalize_repository(value) for value in repositories)
    )
    if not selected or len(selected) > 20:
        raise KnowledgeOAuthError("knowledge_oauth_repository_scope_invalid")
    installations = providers.github_installations(snapshot.access_token)[
        "installations"
    ]
    if installation_id not in {entry["id"] for entry in installations}:
        raise KnowledgeOAuthError("knowledge_oauth_installation_denied")
    available = providers.github_installation_repositories(
        snapshot.access_token, installation_id
    )
    if not set(selected) <= {entry["full_name"] for entry in available["repositories"]}:
        raise KnowledgeOAuthError("knowledge_oauth_repository_scope_denied")
    if not store.save_repositories(
        db, user_id, "github", snapshot.generation, str(installation_id), selected
    ):
        raise KnowledgeOAuthError("knowledge_oauth_flow_superseded")
