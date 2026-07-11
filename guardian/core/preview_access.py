"""Private-preview identity and role policy.

The Cloudflare Tunnel is only a transport boundary.  This module provides the
application boundary used when ``GUARDIAN_EXPOSURE_MODE=private_preview``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from guardian.core.auth_dependencies import resolve_session_user_id

PRIVATE_PREVIEW_EXPOSURE_MODE = "private_preview"
GUEST_ROLE = "guest"
ADMIN_ROLE = "admin"


@dataclass(frozen=True)
class PreviewPrincipal:
    email: str
    role: str


def is_private_preview() -> bool:
    return (
        (os.getenv("GUARDIAN_EXPOSURE_MODE") or "").strip().lower()
        == PRIVATE_PREVIEW_EXPOSURE_MODE
    )


def normalize_preview_email(value: object) -> str:
    email = str(value or "").strip().casefold()
    if not email or "@" not in email or email.startswith("@"):
        return ""
    return email


def _emails_from_env(name: str) -> set[str]:
    return {
        normalized
        for raw in (os.getenv(name) or "").split(",")
        if (normalized := normalize_preview_email(raw))
    }


def preview_admin_emails() -> set[str]:
    return _emails_from_env("CODEXIFY_PREVIEW_ADMIN_EMAILS")


def preview_approved_emails() -> set[str]:
    # An explicitly configured admin is necessarily approved.  This avoids a
    # configuration typo silently locking the only operator out of a preview.
    return _emails_from_env("CODEXIFY_PREVIEW_APPROVED_EMAILS") | preview_admin_emails()


def role_for_preview_email(value: object) -> str | None:
    email = normalize_preview_email(value)
    approved = preview_approved_emails()
    if not email or not approved or email not in approved:
        return None
    return ADMIN_ROLE if email in preview_admin_emails() else GUEST_ROLE


def require_preview_principal(request: Request) -> PreviewPrincipal:
    """Resolve an allowlisted session identity for the private-preview mode."""
    user_id = resolve_session_user_id(
        request.headers.get("Authorization"), request.cookies.get("gc_session")
    )
    role = role_for_preview_email(user_id)
    if not user_id or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Private preview requires an approved authenticated email",
        )
    return PreviewPrincipal(email=normalize_preview_email(user_id), role=role)


def require_preview_admin(request: Request) -> PreviewPrincipal:
    principal = require_preview_principal(request)
    if principal.role != ADMIN_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return principal
