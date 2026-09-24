"""Issue and revoke one-time activations in the private-preview runtime."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.exc import SQLAlchemyError

from guardian.account_activation.service import (
    ActivationAuthorizationError,
    ActivationConflictError,
    ActivationNotFoundError,
    ActivationStateError,
    issue_activation,
    normalize_actor_user_id,
    revoke_activation,
)
from guardian.core.db import load_guardian_db_from_env
from guardian.core.preview_access import (
    PRIVATE_PREVIEW_EXPOSURE_MODE,
    normalize_preview_email,
    role_for_preview_email,
)
from guardian.core.supported_profile import SUPPORTED_PROFILE_ENV

PRIVATE_PREVIEW_PROFILE_NAME = "v1-whooshd-deepseek-web"
REQUIRED_AUTH_MODE = "remote"
DEFAULT_EXPIRY_HOURS = 24
MAX_EXPIRY_HOURS = 7 * 24

_DATABASE_UNAVAILABLE = "authentication database unavailable"
_DATABASE_OPERATION_FAILED = "activation database operation failed"
_POSTURE_MESSAGE = (
    "requires the private-preview runtime: "
    "GUARDIAN_AUTH_MODE=remote, "
    "GUARDIAN_EXPOSURE_MODE=private_preview, "
    "CODEXIFY_SUPPORTED_PROFILE=v1-whooshd-deepseek-web"
)


def runtime_posture_error() -> str | None:
    """Return a bounded error when the canonical private-preview posture is absent."""

    auth_mode = os.getenv("GUARDIAN_AUTH_MODE")
    exposure_mode = os.getenv("GUARDIAN_EXPOSURE_MODE")
    profile = os.getenv(SUPPORTED_PROFILE_ENV)
    if auth_mode is None or exposure_mode is None or profile is None:
        return _POSTURE_MESSAGE
    if auth_mode.strip().lower() != REQUIRED_AUTH_MODE:
        return "requires GUARDIAN_AUTH_MODE=remote"
    if exposure_mode.strip().lower() != PRIVATE_PREVIEW_EXPOSURE_MODE:
        return "requires GUARDIAN_EXPOSURE_MODE=private_preview"
    if profile.strip() != PRIVATE_PREVIEW_PROFILE_NAME:
        return (
            "requires "
            "CODEXIFY_SUPPORTED_PROFILE=v1-whooshd-deepseek-web"
        )
    return None


def normalize_base_url(value: object) -> str:
    """Return a normalized HTTP(S) origin/path with no secret-bearing parts."""

    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise ValueError("base URL must be a valid http(s) URL") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be a valid http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(
            "base URL must not contain credentials, query, or fragment"
        )
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, parsed.path.rstrip("/"), "", "")
    )


def _bounded_expiry_hours(value: str) -> int:
    try:
        hours = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            "expiration must be a whole number of hours"
        ) from exc
    if not 1 <= hours <= MAX_EXPIRY_HOURS:
        raise argparse.ArgumentTypeError(
            f"expiration must be between 1 and {MAX_EXPIRY_HOURS} hours"
        )
    return hours


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Issue or revoke one-time account activation capabilities in the "
            "allowlist-driven private-preview runtime."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue = subparsers.add_parser(
        "issue", description="Issue an allowlist-bound activation URL."
    )
    issue.add_argument("--email", required=True)
    issue.add_argument("--actor-user-id", required=True)
    issue.add_argument("--base-url", required=True)
    issue.add_argument(
        "--expires-in-hours",
        default=DEFAULT_EXPIRY_HOURS,
        type=_bounded_expiry_hours,
    )

    revoke = subparsers.add_parser(
        "revoke", description="Revoke an unconsumed activation by durable ID."
    )
    revoke.add_argument("--activation-id", required=True)
    revoke.add_argument("--actor-user-id", required=True)
    return parser


def _load_db(parser: argparse.ArgumentParser):
    try:
        db = load_guardian_db_from_env()
    except Exception:
        parser.error(_DATABASE_UNAVAILABLE)
    if db is None:
        parser.error(_DATABASE_UNAVAILABLE)
    return db


def _issue(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    email = normalize_preview_email(args.email)
    role = role_for_preview_email(email)
    if role is None:
        parser.error("email is not in the configured preview allowlist")

    try:
        actor_user_id = normalize_actor_user_id(args.actor_user_id)
        base_url = normalize_base_url(args.base_url)
    except (ValueError, ActivationAuthorizationError) as exc:
        parser.error(str(exc))

    current = datetime.now(timezone.utc)
    expires_at = current + timedelta(hours=args.expires_in_hours)
    db = _load_db(parser)
    try:
        with db.get_session() as session:
            issued = issue_activation(
                session,
                recipient_email=email,
                intended_role=role,
                created_by_user_id=actor_user_id,
                expires_at=expires_at,
                now=current,
            )
            session.commit()
            activation_id = issued.capability.activation_id
            persisted_expiry = issued.capability.expires_at
            activation_url = f"{base_url}/activate#token={issued.raw_token}"
    except SQLAlchemyError:
        parser.error(_DATABASE_OPERATION_FAILED)
    except (ActivationAuthorizationError, ActivationConflictError, ValueError) as exc:
        parser.error(str(exc))

    print(f"Activation ID: {activation_id}")
    print(f"Expires at: {persisted_expiry.isoformat()}")
    print(f"Activation URL: {activation_url}")
    return 0


def _revoke(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    try:
        actor_user_id = normalize_actor_user_id(args.actor_user_id)
    except ActivationAuthorizationError as exc:
        parser.error(str(exc))
    db = _load_db(parser)
    try:
        with db.get_session() as session:
            capability = revoke_activation(
                session,
                activation_id=args.activation_id,
                actor_user_id=actor_user_id,
            )
            session.commit()
            activation_id = capability.activation_id
            revoked_at = capability.revoked_at
    except SQLAlchemyError:
        parser.error(_DATABASE_OPERATION_FAILED)
    except (
        ActivationAuthorizationError,
        ActivationNotFoundError,
        ActivationStateError,
    ) as exc:
        parser.error(str(exc))

    print(f"Revoked activation: {activation_id}")
    print(f"Revoked at: {revoked_at.isoformat()}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    posture_error = runtime_posture_error()
    if posture_error is not None:
        parser.error(posture_error)

    if args.command == "issue":
        return _issue(parser, args)
    return _revoke(parser, args)


if __name__ == "__main__":
    raise SystemExit(main())
