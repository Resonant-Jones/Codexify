"""Operator-only account provisioning for the private-preview allowlist."""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timezone

from guardian.core.db import load_guardian_db_from_env
from guardian.core.passwords import hash_password
from guardian.core.preview_access import (
    is_private_preview,
    normalize_preview_email,
    role_for_preview_email,
)
from guardian.db.models import User


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or reset an allowlisted private-preview account."
    )
    parser.add_argument("--email", required=True, help="Approved account email")
    args = parser.parse_args()

    if not is_private_preview():
        parser.error("requires GUARDIAN_EXPOSURE_MODE=private_preview")

    email = normalize_preview_email(args.email)
    role = role_for_preview_email(email)
    if role is None:
        parser.error("email is not in the configured preview allowlist")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password or password != confirmation:
        parser.error("passwords must be non-empty and match")

    db = load_guardian_db_from_env()
    if db is None:
        parser.error("authentication database unavailable")

    with db.get_session() as session:
        user = session.get(User, email)
        if user is None:
            user = User(
                id=email,
                username=email,
                password_hash=hash_password(password),
                role=role,
                created_at=datetime.now(timezone.utc),
            )
            session.add(user)
        else:
            user.username = email
            user.password_hash = hash_password(password)
            user.role = role
        session.commit()

    print(f"Provisioned {email} with {role} role.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
