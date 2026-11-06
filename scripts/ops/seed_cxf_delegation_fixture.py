#!/usr/bin/env python3
"""Seed a disposable Codexify PostgreSQL database for the delegated-coding proof.

The seeder writes every row through the application's own ORM models and the
application's own database loader (``guardian.core.db.load_guardian_db_from_env``).
No raw SQL is used for inserts. The fixture repository is bound to the seeded
Project as an ``external_linked`` ``RepositoryBinding``, and the binding is
verified with the application's canonical resolver
(``guardian.core.repository_authority.resolve_project_repository_binding``)
before the transaction is committed.

Environment:
    CXF_ACCOUNT_ID       (required) account/user id to seed
    CXF_ACCOUNT_PASSWORD (required) password for that account
    CXF_FIXTURE_REPO     (required) path to the fixture git repository
    CXF_PROJECT_NAME     (optional) project name; defaults to a stable
                         per-account name

The script prints a JSON summary to stdout and never prints the password.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from guardian.core.db import load_guardian_db_from_env  # noqa: E402
from guardian.core.passwords import hash_password  # noqa: E402
from guardian.core.repository_authority import (  # noqa: E402
    SOURCE_CLASS_EXTERNAL_LINKED,
    resolve_project_repository_binding,
)
from guardian.db.models import (  # noqa: E402
    ChatMessage,
    ChatThread,
    Project,
    RepositoryBinding,
    User,
    UserProfile,
)
from guardian.messaging.service import get_or_create_local_node  # noqa: E402

DEFAULT_PROJECT_NAME_SUFFIX = "cxf-delegation-fixture"
THREAD_TITLE = "CXF delegation fixture"
SOURCE_MESSAGE_CONTENT = (
    "Delegation fixture source message: apply the requested change to the "
    "fixture repository working tree."
)
BINDING_PROVENANCE = {
    "registration_source": "cxf_delegation_fixture_seeder",
    "operation_class": "external_linked",
}


class SeedError(RuntimeError):
    """Fatal, operator-actionable seeding failure."""


def _fail(message: str) -> NoReturn:
    print(f"cxf-seeder: {message}", file=sys.stderr)
    raise SystemExit(2)


def _git_top_level(path: str) -> str:
    """Return the exact Git working-tree top level of ``path``."""
    completed = subprocess.run(
        ["git", "-C", path, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise SeedError(
            f"git rev-parse --show-toplevel failed for {path!r} "
            f"(rc={completed.returncode}): {stderr[:300]}"
        )
    stdout = (completed.stdout or "").strip()
    if not stdout:
        raise SeedError(
            f"git rev-parse --show-toplevel returned empty output for {path!r}"
        )
    top_level = stdout.splitlines()[-1].strip()
    # Normalize the same way the application's repository authority layer does
    # (strict symlink-aware resolution) so the stored canonical root compares
    # equal to the root the resolver observes.
    return str(Path(top_level).resolve())


def _ensure_user(session: Session, account_id: str, password: str) -> User:
    user = session.get(User, account_id)
    if user is None:
        user = User(
            id=account_id,
            username=account_id,
            password_hash=hash_password(password),
            role="admin",
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    changed = False
    if user.username != account_id:
        user.username = account_id
        changed = True
    if user.role != "admin":
        user.role = "admin"
        changed = True
    # Re-hash so the seeded credential always matches CXF_ACCOUNT_PASSWORD.
    user.password_hash = hash_password(password)
    changed = True
    if changed:
        session.commit()
        session.refresh(user)
    return user


def _ensure_profile(session: Session, account_id: str) -> UserProfile:
    """Create the account's canonical social profile.

    Mirrors ``guardian.messaging.service.get_or_create_owned_profile``: the
    profile row is created for the account, ``profile_id`` is a freshly minted
    UUID hex token, ``node_id`` is the canonical local ThreadSpace node, and
    ``username_state`` starts as ``unset``.
    """
    profile = session.scalar(
        select(UserProfile).where(UserProfile.user_id == account_id)
    )
    if profile is None:
        node = get_or_create_local_node(session)
        profile = UserProfile(
            user_id=account_id,
            profile_id=uuid.uuid4().hex,
            node_id=node.node_id,
            username_state="unset",
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile

    changed = False
    if not profile.profile_id:
        profile.profile_id = uuid.uuid4().hex
        changed = True
    if not profile.node_id:
        profile.node_id = get_or_create_local_node(session).node_id
        changed = True
    if profile.username_state is None:
        profile.username_state = "unset"
        changed = True
    if changed:
        session.commit()
        session.refresh(profile)
    return profile


def _ensure_project(session: Session, account_id: str, name: str) -> Project:
    project = session.scalar(
        select(Project).where(
            Project.user_id == account_id,
            Project.name == name,
        )
    )
    if project is None:
        project = Project(
            user_id=account_id,
            name=name,
            description="Disposable project for the delegated-coding proof.",
            identity_depth="light",
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        return project
    return project


def _ensure_thread(
    session: Session, account_id: str, project: Project
) -> ChatThread:
    thread = session.scalar(
        select(ChatThread).where(
            ChatThread.user_id == account_id,
            ChatThread.project_id == project.id,
            ChatThread.title == THREAD_TITLE,
        )
    )
    if thread is None:
        thread = ChatThread(
            user_id=account_id,
            title=THREAD_TITLE,
            summary="",
            project_id=project.id,
            origin_system="codexify",
        )
        session.add(thread)
        session.commit()
        session.refresh(thread)
    return thread


def _ensure_source_message(
    session: Session, account_id: str, thread: ChatThread
) -> ChatMessage:
    message = session.scalar(
        select(ChatMessage).where(
            ChatMessage.thread_id == thread.id,
            ChatMessage.user_id == account_id,
            ChatMessage.role == "user",
            ChatMessage.content == SOURCE_MESSAGE_CONTENT,
        )
    )
    if message is None:
        message = ChatMessage(
            thread_id=thread.id,
            user_id=account_id,
            role="user",
            content=SOURCE_MESSAGE_CONTENT,
            kind="chat",
            extra_meta={},
        )
        session.add(message)
        session.commit()
        session.refresh(message)
    return message


def _ensure_binding(
    session: Session, account_id: str, project: Project, canonical_root: str
) -> str:
    """Create and verify the active RepositoryBinding for ``project``.

    The binding row is flushed but not committed until the application's own
    resolver confirms that the written row actually resolves. Any resolution
    failure rolls the transaction back.
    """
    existing = session.scalar(
        select(RepositoryBinding).where(
            RepositoryBinding.project_id == project.id,
            RepositoryBinding.is_active.is_(True),
        )
    )
    if existing is None:
        binding = RepositoryBinding(
            id=str(uuid.uuid4()),
            project_id=project.id,
            source_class=SOURCE_CLASS_EXTERNAL_LINKED,
            canonical_root=canonical_root,
            is_active=True,
            provenance=dict(BINDING_PROVENANCE),
        )
        session.add(binding)
        session.flush()
        binding_id = binding.id
    else:
        binding = existing
        binding_id = binding.id
        if str(binding.canonical_root) != canonical_root:
            raise SeedError(
                "project already has an active RepositoryBinding for a different "
                f"canonical root ({binding.canonical_root!r} != {canonical_root!r}); "
                "refusing to replace it."
            )

    try:
        resolved = resolve_project_repository_binding(
            session,
            authenticated_account_id=account_id,
            project_id=project.id,
        )
    except Exception as exc:  # noqa: BLE001 - fail closed on any resolution error
        session.rollback()
        raise SeedError(
            "RepositoryBinding did not resolve through "
            "resolve_project_repository_binding; transaction rolled back: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if str(resolved.canonical_root) != canonical_root:
        session.rollback()
        raise SeedError(
            "resolved canonical root "
            f"({resolved.canonical_root!r}) does not match the fixture root "
            f"({canonical_root!r}); transaction rolled back."
        )

    session.commit()
    return str(binding_id)


def main(argv: list[str] | None = None) -> int:
    del argv  # the seeder is configured entirely through the environment

    account_id = (os.environ.get("CXF_ACCOUNT_ID") or "").strip()
    if not account_id:
        _fail("CXF_ACCOUNT_ID is required")

    fixture_repo = (os.environ.get("CXF_FIXTURE_REPO") or "").strip()
    if not fixture_repo:
        _fail("CXF_FIXTURE_REPO is required")

    password = os.environ.get("CXF_ACCOUNT_PASSWORD") or ""
    if not password:
        _fail("CXF_ACCOUNT_PASSWORD is required")

    project_name = (os.environ.get("CXF_PROJECT_NAME") or "").strip()
    if not project_name:
        project_name = f"{DEFAULT_PROJECT_NAME_SUFFIX}-{account_id}"

    try:
        canonical_root = _git_top_level(fixture_repo)
    except SeedError as exc:
        _fail(str(exc))

    db = load_guardian_db_from_env()
    if db is None:
        _fail(
            "no database configured: set GUARDIAN_DATABASE_URL (or DATABASE_URL) "
            "for the disposable Codexify stack"
        )

    summary: dict[str, Any] = {}
    with db.get_session() as session:
        try:
            _ensure_user(session, account_id, password)
            _ensure_profile(session, account_id)
            project = _ensure_project(session, account_id, project_name)
            thread = _ensure_thread(session, account_id, project)
            message = _ensure_source_message(session, account_id, thread)
            _ensure_binding(session, account_id, project, canonical_root)
        except SeedError as exc:
            session.rollback()
            _fail(str(exc))
        except Exception as exc:  # noqa: BLE001 - never leave a half-open tx
            session.rollback()
            _fail(f"seeding failed: {type(exc).__name__}: {exc}")

        summary = {
            "account_id": account_id,
            "project_id": int(project.id),
            "thread_id": int(thread.id),
            "source_message_id": int(message.id),
            "canonical_root": canonical_root,
        }

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
