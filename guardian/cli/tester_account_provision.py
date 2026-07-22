"""Operator-only account provisioning for the stabilized tester runtime.

This command targets the stabilized friends-and-family tester runtime
(``codexify_tester``) which uses remote session authentication with the
``local_safe`` exposure mode and the ``v1-friends-family-web`` supported
profile. It is intentionally separate from
:mod:`guardian.cli.private_preview_provision`, which belongs to the older
allowlist-driven ``private_preview`` contract and must remain isolated.

The command creates or resets a canonical Guardian ``users`` row. Guardian
remains the only account and role authority; this module never edits account
records with raw SQL, never creates a second user store, and never widens the
persisted role vocabulary beyond the canonical ``admin`` and ``guest`` tokens.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import datetime, timezone

from guardian.core.db import load_guardian_db_from_env
from guardian.core.passwords import hash_password
from guardian.core.preview_access import ADMIN_ROLE, GUEST_ROLE
from guardian.core.supported_profile import SUPPORTED_PROFILE_ENV
from guardian.db.models import User

# Canonical tokens reused from their existing homes. These mirror the values
# enforced elsewhere; they are not a second role/mode-token domain.
TESTER_PROFILE_NAME = "v1-friends-family-web"
REQUIRED_AUTH_MODE = "remote"
REQUIRED_EXPOSURE_MODE = "local_safe"
CANONICAL_ROLES = (ADMIN_ROLE, GUEST_ROLE)

_DATABASE_UNAVAILABLE = "authentication database unavailable"
_POSTURE_MESSAGE = (
    "requires the stabilized tester runtime: "
    "GUARDIAN_AUTH_MODE=remote, "
    "GUARDIAN_EXPOSURE_MODE=local_safe, "
    "CODEXIFY_SUPPORTED_PROFILE=v1-friends-family-web"
)


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the tester account provisioner."""
    parser = argparse.ArgumentParser(
        description=(
            "Create or reset an operator-authorized account in the "
            "stabilized friends-and-family tester runtime "
            "(codexify_tester)."
        ),
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Account email; normalized, trimmed, and case-folded to the canonical id.",
    )
    parser.add_argument(
        "--role",
        choices=list(CANONICAL_ROLES),
        default=None,
        help=(
            "Canonical role ('admin' or 'guest'). Required to create a new "
            "account; optional for an existing account, where omitting it "
            "preserves the current role."
        ),
    )
    return parser


def runtime_posture_error() -> str | None:
    """Return a bounded error string if the tester posture is not active.

    A missing runtime variable fails closed rather than inheriting an assumed
    value. The returned message names only the required posture and never
    prints unrelated environment values.
    """
    auth_mode = os.getenv("GUARDIAN_AUTH_MODE")
    exposure_mode = os.getenv("GUARDIAN_EXPOSURE_MODE")
    profile = os.getenv(SUPPORTED_PROFILE_ENV)
    if auth_mode is None or exposure_mode is None or profile is None:
        return _POSTURE_MESSAGE
    if auth_mode.strip().lower() != REQUIRED_AUTH_MODE:
        return "requires GUARDIAN_AUTH_MODE=remote"
    if exposure_mode.strip().lower() != REQUIRED_EXPOSURE_MODE:
        return "requires GUARDIAN_EXPOSURE_MODE=local_safe"
    if profile.strip() != TESTER_PROFILE_NAME:
        return "requires CODEXIFY_SUPPORTED_PROFILE=v1-friends-family-web"
    return None


def normalize_email(value: object) -> str:
    """Normalize an email into its canonical id form.

    Converts to string, trims whitespace, and case-folds. Rejects empty values
    and values without a nonempty local part and domain component.
    """
    email = str(value or "").strip().casefold()
    if not email:
        raise ValueError("email is required")
    if "@" not in email:
        raise ValueError("email must have a nonempty local part and domain")
    local, _, domain = email.partition("@")
    if not local or not domain:
        raise ValueError("email must have a nonempty local part and domain")
    return email


def resolve_role(existing_role: str | None, role_arg: str | None) -> tuple[str, str]:
    """Resolve the (outcome, role) to apply for an account.

    ``existing_role`` is ``None`` when the account does not exist yet.

    - new account: ``--role`` is required;
    - existing account with a noncanonical persisted role: refused;
    - existing account without ``--role``: role preserved;
    - existing account with ``--role``: role explicitly assigned.

    The returned ``outcome`` is one of ``create``, ``reset_preserve``, or
    ``reset_assign``.
    """
    if existing_role is None:
        if role_arg is None:
            raise ValueError("--role is required to create a new account")
        return ("create", role_arg)
    if existing_role not in CANONICAL_ROLES:
        raise ValueError(
            "existing account has a noncanonical role; refusing to change it"
        )
    if role_arg is None:
        return ("reset_preserve", existing_role)
    return ("reset_assign", role_arg)


def apply_account_mutation(
    session,
    user: User | None,
    email: str,
    role: str,
    password: str,
) -> None:
    """Stage the account mutation in the session without committing.

    The caller is responsible for committing exactly once after the complete
    mutation is ready. ``hash_password`` owns password hashing; no plaintext
    password is ever stored.
    """
    password_hash = hash_password(password)
    if user is None:
        session.add(
            User(
                id=email,
                username=email,
                password_hash=password_hash,
                role=role,
                created_at=datetime.now(timezone.utc),
            )
        )
        return
    user.username = email
    user.password_hash = password_hash
    user.role = role


def success_message(email: str, role: str, outcome: str) -> str:
    """Build a bounded success message that never discloses the hash."""
    if outcome == "create":
        return f"Created account {email} with role {role}."
    if outcome == "reset_preserve":
        return f"Reset password for {email}; role {role} preserved."
    return f"Reset password for {email}; role set to {role}."


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    posture_error = runtime_posture_error()
    if posture_error is not None:
        parser.error(posture_error)

    try:
        email = normalize_email(args.email)
    except ValueError as exc:
        parser.error(str(exc))

    if not sys.stdin.isatty():
        parser.error("requires an interactive terminal for password entry")

    try:
        db = load_guardian_db_from_env()
    except Exception:
        parser.error(_DATABASE_UNAVAILABLE)
    if db is None:
        parser.error(_DATABASE_UNAVAILABLE)

    with db.get_session() as session:
        user = session.get(User, email)
        existing_role = getattr(user, "role", None) if user is not None else None
        try:
            outcome, role = resolve_role(existing_role, args.role)
        except ValueError as exc:
            parser.error(str(exc))

        password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if not password or password != confirmation:
            parser.error("passwords must be non-empty and match")

        apply_account_mutation(session, user, email, role, password)
        session.commit()

    print(success_message(email, role, outcome))
    return 0


if __name__ == "__main__":
    sys.exit(main())
