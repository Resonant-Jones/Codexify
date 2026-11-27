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
    resolve_accepted_chat_work_identity,
)
from guardian.core.db import (
    build_native_origin_assertion,
    create_chat_completion_attempt,
    freeze_chat_tool_decision,
    mark_chat_completion_attempt_accepted,
)
from guardian.core.dependencies import RequestUserScope
from guardian.db.models import (
    ChatCompletionAttempt,
    ChatMessage,
    ChatThread,
    Project,
    User,
)
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline

COMMAND = "op::notion_content_search"
HASH = "a" * 64


@pytest.fixture
def store(monkeypatch):
    # Portable test schema mirrors columns only. It deliberately does NOT claim
    # PostgreSQL constraints, row locking or the migration's trigger were tested.
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    for model in (User, Project, ChatThread, ChatMessage, ChatCompletionAttempt):
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
    message_id=None,
    checkpoint=True,
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
        latest_turn_message_id=message_id,
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
        accepted_user_message_id=message_id if custody else None,
    )
    if checkpoint:
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


def seed_source(store, *, message_id=11, thread=1, account="a@example.com"):
    with store._sa_session() as session:
        session.add(
            ChatMessage(
                id=message_id,
                thread_id=thread,
                user_id=account,
                role="user",
                kind="chat",
                content="not returned by identity resolution",
                extra_meta=build_native_origin_assertion().as_metadata(),
            )
        )


def accepted_source_work(store, **kwargs):
    seed_source(store)
    return seed(store, message_id=11, checkpoint=False, **kwargs)


def test_identity_is_content_free_and_resolves_a_b_a_without_checkpoints(store):
    a = accepted_source_work(store)
    seed_source(store, message_id=12, thread=2, account="b@example.com")
    b = seed(
        store, account="b@example.com", thread=2, suffix="b",
        message_id=12, checkpoint=False,
    )
    first = resolve_accepted_chat_work_identity(store, a)
    second = resolve_accepted_chat_work_identity(store, b)
    assert (first.account_id, first.accepted_user_message_id) == ("a@example.com", 11)
    assert (second.account_id, second.accepted_user_message_id) == ("b@example.com", 12)
    assert resolve_accepted_chat_work_identity(store, a) == first
    assert vars(first) == {
        "account_id": a.user_id,
        "request_id": a.request_id,
        "backend_task_id": a.task_id,
        "thread_id": a.thread_id,
        "turn_id": a.turn_id,
        "accepted_user_message_id": 11,
        "current_project_id": None,
    }
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(store, a)


@pytest.mark.parametrize(
    "field,value",
    [
        ("latest_turn_message_id", 12),  # same thread
        ("latest_turn_message_id", 13),  # another thread, same account
        ("latest_turn_message_id", 14),  # another account
        ("latest_turn_message_id", None),
        ("latest_turn_message_id", "11"),
        ("user_id", "b@example.com"),
        ("thread_id", 2),
        ("task_id", "substituted"),
        ("request_id", "substituted"),
        ("turn_id", "substituted"),
        ("origin", "worker:voice_turn"),
        ("hosted_room_invocation", {}),
        ("work_deadline_at", "2026-11-27T18:15:00+00:00"),
    ],
)
def test_preselection_rejects_queue_substitution(store, field, value):
    task = accepted_source_work(store)
    seed_source(store, message_id=12)
    seed_source(store, message_id=13, thread=3)
    seed_source(store, message_id=14, thread=2, account="b@example.com")
    setattr(task, field, value)
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


@pytest.mark.parametrize("custody,old", [(False, False), (True, True)])
def test_preselection_refuses_legacy_account_custody_and_expiry(store, custody, old):
    task = accepted_source_work(store, custody=custody, old=old)
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


def test_preselection_refuses_legacy_source_even_with_checkpoint(store):
    task = seed(store)
    seed_source(store)
    task.latest_turn_message_id = 11
    assert resolve(store, task).account_id == task.user_id
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


def test_preselection_rereads_after_pending_then_rejects_deleted_source(store):
    task = accepted_source_work(store, accepted=False)
    with pytest.raises(ChatAccountAcceptancePending):
        resolve_accepted_chat_work_identity(store, task)
    mark_chat_completion_attempt_accepted(store, backend_task_id=task.task_id)
    first = resolve_accepted_chat_work_identity(store, task)
    seed_source(store, message_id=12)
    with store._sa_session() as session:
        session.delete(session.get(ChatMessage, 11))
    assert first.accepted_user_message_id == 11
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)
    task.latest_turn_message_id = 12
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


@pytest.mark.parametrize(
    "target,field,value",
    [
        (ChatMessage, "role", "assistant"),
        (ChatMessage, "kind", "fact_evidence"),
        (ChatMessage, "user_id", "b@example.com"),
        (ChatMessage, "thread_id", 2),
        (ChatMessage, "extra_meta", {"origin": "chatgpt_import"}),
        (ChatThread, "user_id", "b@example.com"),
        (ChatCompletionAttempt, "terminal_event_type", "task.cancelled"),
        (ChatCompletionAttempt, "terminal_event_type", "task.failed"),
        (ChatCompletionAttempt, "completed_message_id", 99),
    ],
)
def test_preselection_rechecks_eligibility_and_terminal_state_on_retry(
    store, target, field, value
):
    task = accepted_source_work(store)
    assert resolve_accepted_chat_work_identity(store, task).account_id == task.user_id
    key = {ChatMessage: 11, ChatThread: 1, ChatCompletionAttempt: task.request_id}
    with store._sa_session() as session:
        setattr(session.get(target, key[target]), field, value)
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


def test_preselection_current_project_is_placement_and_conflict_denies(store):
    task = accepted_source_work(store)
    with store._sa_session() as session:
        session.add(Project(id=10, name="current", user_id=task.user_id))
        session.get(ChatThread, 1).project_id = 10
    assert resolve_accepted_chat_work_identity(store, task).current_project_id == 10
    with store._sa_session() as session:
        session.get(Project, 10).description = (
            '{"__codexify_project_owner__": true, "owner_user_id": "b@example.com"}'
        )
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


def test_preselection_rereads_preview_eligibility(store, monkeypatch):
    task = accepted_source_work(store)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", task.user_id)
    monkeypatch.delenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", raising=False)
    assert resolve_accepted_chat_work_identity(store, task).account_id == task.user_id
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "")
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


def test_preselection_denies_cancelled_and_unavailable_authority(store, monkeypatch):
    task = accepted_source_work(store)
    assert resolve_accepted_chat_work_identity(store, task).account_id == task.user_id
    monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: True)
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)

    def unavailable(*_args):
        raise RuntimeError("private diagnostic")

    monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", unavailable)
    with pytest.raises(
        ChatAccountCustodyUnavailable, match="^accepted_chat_account_unavailable$"
    ):
        resolve_accepted_chat_work_identity(store, task)
    with pytest.raises(
        ChatAccountCustodyUnavailable, match="^accepted_chat_account_unavailable$"
    ):
        resolve_accepted_chat_work_identity(SimpleNamespace(_sa_session=unavailable), task)


@pytest.mark.parametrize(
    "field,value",
    [
        ("role", "assistant"),
        ("kind", "fact_evidence"),
        ("thread_id", 2),
        ("user_id", "b@example.com"),
    ],
)
def test_canonical_mismatch_fails_source_binding_at_creation(store, field, value):
    seed_source(store)
    with store._sa_session() as session:
        setattr(session.get(ChatMessage, 11), field, value)
    task = seed(store, message_id=11, checkpoint=False)
    with store._sa_session() as session:
        attempt = session.get(ChatCompletionAttempt, task.request_id)
        assert attempt.accepted_user_message_id is None
        assert attempt.accepted_account_id == task.user_id
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)


def test_preselection_refuses_deleted_account(store):
    task = accepted_source_work(store)
    with store._sa_session() as session:
        session.delete(session.get(User, task.user_id))
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)
