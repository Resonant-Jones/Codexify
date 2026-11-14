"""Hermetic database-backed prerequisite semantics, not PostgreSQL conformance."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from guardian.core.chat_account_custody import (
    ChatAccountAcceptancePending,
    ChatAccountCustodyUnavailable,
    ordinary_chat_acceptance_account,
    resolve_accepted_chat_account,
)
from guardian.core.db import create_chat_completion_attempt, freeze_chat_tool_decision
from guardian.core.dependencies import RequestUserScope
from guardian.db.models import ChatCompletionAttempt, ChatThread, Project, User
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline

COMMAND = "op::notion_content_search"
HASH = "a" * 64


@pytest.fixture
def store(monkeypatch):
    # Portable test schema mirrors columns only. It deliberately does NOT claim
    # PostgreSQL constraints, row locking or the migration's trigger were tested.
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    for model in (User, Project, ChatThread, ChatCompletionAttempt):
        sa.Table(
            model.__tablename__,
            metadata,
            *[
                sa.Column(
                    c.name,
                    c.type.as_generic(),
                    primary_key=c.primary_key,
                    nullable=True,
                )
                for c in model.__table__.columns
            ],
        )
    metadata.create_all(engine)
    Session = sessionmaker(engine)

    @contextmanager
    def session():
        with Session.begin() as db:
            yield db

    repo = SimpleNamespace(_sa_session=session)
    monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: False)
    with session() as db:
        db.add_all(
            [
                User(id="a@example.com", username="a", password_hash="inert"),
                User(id="b@example.com", username="b", password_hash="inert"),
            ]
        )
        db.add_all(
            [
                ChatThread(id=1, user_id="a@example.com", title="A"),
                ChatThread(id=2, user_id="b@example.com", title="B"),
            ]
        )
    yield repo
    engine.dispose()


def seed(
    repo,
    *,
    account="a@example.com",
    thread=1,
    suffix="a",
    accepted=True,
    old=False,
    custody=True,
):
    now = datetime.now(timezone.utc)
    deadline = build_accepted_chat_task_deadline(
        now - timedelta(hours=1) if old else now
    )
    task = SimpleNamespace(
        request_id=f"req-{suffix}",
        task_id=f"task-{suffix}",
        thread_id=thread,
        turn_id=f"turn-{suffix}",
        user_id=account,
        origin="api:chat.complete",
        hosted_room_invocation=None,
        **deadline.to_dict(),
    )
    create_chat_completion_attempt(
        repo,
        request_id=task.request_id,
        backend_task_id=task.task_id,
        thread_id=thread,
        turn_id=task.turn_id,
        deadline_snapshot=deadline,
        turn_lock_token="inert-test-lock",
        accepted_account_id=account if custody else None,
    )
    freeze_chat_tool_decision(
        repo,
        request_id=task.request_id,
        backend_task_id=task.task_id,
        thread_id=thread,
        turn_id=task.turn_id,
        account_id=account,
        command_id=COMMAND,
        args_hash=HASH,
    )
    if accepted:
        with repo._sa_session() as db:
            db.get(ChatCompletionAttempt, task.request_id).accepted_at = now
    return task


def resolve(repo, task):
    return resolve_accepted_chat_account(repo, task, command_id=COMMAND, args_hash=HASH)


def test_real_row_resolves_canonical_owner_and_sequential_accounts(store):
    a = seed(store)
    b = seed(store, account="b@example.com", thread=2, suffix="b")
    assert resolve(store, a).account_id == "a@example.com"
    assert resolve(store, b).account_id == "b@example.com"
    assert resolve(store, a).account_id == "a@example.com"


@pytest.mark.parametrize(
    "field,value",
    [
        ("user_id", "b@example.com"),
        ("thread_id", 2),
        ("task_id", "other"),
        ("request_id", "other"),
        ("turn_id", "other"),
        ("origin", "worker:voice_turn"),
        ("hosted_room_invocation", {}),
        ("work_deadline_at", "invalid"),
    ],
)
def test_untrusted_task_fields_cannot_select_authority(store, field, value):
    task = seed(store)
    setattr(task, field, value)
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, task)


@pytest.mark.parametrize("custody,old", [(False, False), (True, True)])
def test_legacy_or_expired_attempt_cannot_authorize(store, custody, old):
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, seed(store, custody=custody, old=old))


def test_publication_race_denies_then_rereads_after_acceptance(store):
    task = seed(store, accepted=False)
    with pytest.raises(ChatAccountAcceptancePending):
        resolve(store, task)
    with store._sa_session() as db:
        db.get(ChatCompletionAttempt, task.request_id).accepted_at = datetime.now(
            timezone.utc
        )
    assert resolve(store, task).account_id == task.user_id


@pytest.mark.parametrize(
    "mutation", ["owner", "user", "project", "terminal", "completed", "hash", "command"]
)
def test_live_state_rechecked_on_retry(store, mutation):
    task = seed(store)
    assert resolve(store, task).account_id == task.user_id
    with store._sa_session() as db:
        row = db.get(ChatCompletionAttempt, task.request_id)
        if mutation == "owner":
            db.get(ChatThread, 1).user_id = "b@example.com"
        elif mutation == "user":
            db.delete(db.get(User, task.user_id))
        elif mutation == "project":
            db.add(Project(id=10, name="other", user_id="b@example.com"))
            db.get(ChatThread, 1).project_id = 10
        elif mutation == "terminal":
            row.terminal_event_type = "task.cancelled"
        elif mutation == "completed":
            row.completed_message_id = 10
        elif mutation == "hash":
            row.tool_args_hash = "b" * 64
        else:
            row.tool_command_id = "op::other"
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, task)


def test_cancellation_and_unavailable_cancel_store_deny(store, monkeypatch):
    task = seed(store)
    monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: True)
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, task)

    def unavailable(_):
        raise RuntimeError("private diagnostic must not leak")

    monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", unavailable)
    with pytest.raises(
        ChatAccountCustodyUnavailable, match="^accepted_chat_account_unavailable$"
    ):
        resolve(store, task)


def test_preview_eligibility_is_live_and_separate(store, monkeypatch):
    task = seed(store)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", task.user_id)
    monkeypatch.delenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", raising=False)
    assert resolve(store, task).account_id == task.user_id
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "")
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, task)


def test_scope_handoff_is_explicit_and_preserves_subject_mapping():
    task = SimpleNamespace(
        user_id="account-a", origin="api:chat.complete", hosted_room_invocation=None
    )
    assert ordinary_chat_acceptance_account(task, None) is None
    assert (
        ordinary_chat_acceptance_account(task, RequestUserScope(user_id="account-a"))
        is None
    )
    scope = RequestUserScope(
        user_id="account-a",
        account_id="account-a",
        subject_id="external-subject",
        multi_user_enabled=True,
    )
    assert ordinary_chat_acceptance_account(task, scope) == "account-a"
    task.hosted_room_invocation = {}
    with pytest.raises(ChatAccountCustodyUnavailable):
        ordinary_chat_acceptance_account(task, scope)


@pytest.mark.parametrize(
    "scope",
    [
        "account-a",
        RequestUserScope(user_id="b", account_id="b"),
        RequestUserScope(user_id="a", account_id="b"),
    ],
)
def test_caller_account_claim_not_an_authenticated_context(scope):
    task = SimpleNamespace(
        user_id="a", origin="api:chat.complete", hosted_room_invocation=None
    )
    with pytest.raises(ChatAccountCustodyUnavailable):
        ordinary_chat_acceptance_account(task, scope)


def test_conflicting_legacy_project_owner_denies(store):
    task = seed(store)
    with store._sa_session() as db:
        db.add(
            Project(
                id=10,
                name="conflict",
                user_id=task.user_id,
                description='{"__codexify_project_owner__": true, "owner_user_id": "b@example.com"}',
            )
        )
        db.get(ChatThread, 1).project_id = 10
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, task)


def test_prepare_does_not_create_account_custody_from_queue_claim(store):
    task = seed(store, custody=False)
    # Correct row IDs and current owner are still not original acceptance proof.
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, task)
