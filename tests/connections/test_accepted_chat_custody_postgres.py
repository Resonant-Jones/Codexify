"""ADR-112 prerequisite proof, not a dispatcher or provider execution grant.

Opt in with CODEXIFY_DISPATCH_TEST_DATABASE_URL pointing to a fresh
dispatch_proof database on a private /tmp/codexify-oauth-pg.*/socket cluster.
These tests use real migrations/rows and synthetic OAuth credentials only.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.command_bus.redaction_policy import compute_args_hash
from guardian.connections import chat_pilot, oauth_store
from guardian.core.chat_account_custody import (
    ChatAccountAcceptancePending,
    ChatAccountCustodyUnavailable,
    ordinary_chat_acceptance_account,
    resolve_accepted_chat_account,
)
from guardian.core.db import (
    create_chat_completion_attempt,
    freeze_chat_tool_decision,
    mark_chat_completion_attempt_accepted,
)
from guardian.core.dependencies import RequestUserScope
from guardian.db.models import ChatCompletionAttempt, ChatThread, Project, User
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from tests.services.test_memory_vault_read_projection import _migrate_to_head


@pytest.fixture(scope="module")
def engine():
    raw = os.getenv("CODEXIFY_DISPATCH_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("explicit disposable dispatch PostgreSQL URL required")
    url = make_url(raw)
    socket = Path(str(url.query.get("host", ""))).resolve()
    assert url.drivername == "postgresql+psycopg"
    assert url.host is None and url.database == "dispatch_proof"
    assert socket.name == "socket"
    assert str(socket).startswith(("/tmp/codexify-oauth-pg.", "/private/tmp/codexify-oauth-pg."))
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SHOW listen_addresses")).scalar_one() == ""
        assert conn.execute(text("SELECT current_database()")).scalar_one() == "dispatch_proof"
    _migrate_to_head(raw)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine, monkeypatch):
    # Only the guarded, newly created disposable database can reach this reset.
    with engine.begin() as conn:
        # OAuth tombstones intentionally have no user foreign key, so CASCADE
        # alone does not isolate their credentials/flows between test cases.
        conn.execute(text("TRUNCATE users, chat_completion_attempts, knowledge_oauth_credentials, knowledge_oauth_flows CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def custody_session():
        with factory.begin() as session:
            yield session

    @contextmanager
    def oauth_session():
        with factory() as session:
            yield session

    monkeypatch.setenv("GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
    monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: False)

    def no_provider_request(*args, **kwargs):
        raise AssertionError("Provider HTTP is forbidden in this prerequisite proof")

    monkeypatch.setattr("requests.sessions.Session.request", no_provider_request)
    with factory.begin() as session:
        session.add_all([User(id=x, username=x, password_hash="synthetic") for x in ("a", "b")])
        session.flush()
        session.add_all([ChatThread(id=1, user_id="a", title="A"), ChatThread(id=2, user_id="b", title="B")])
    return SimpleNamespace(_sa_session=custody_session, get_session=oauth_session)


def accepted(db, owner="a", provider="notion", *, acknowledged=True, legacy=False, expired=False):
    command = f"op::{provider}_content_search"
    raw = {"query": "synthetic"}
    if provider == "github":
        raw["repository"] = "example/selected"
    arguments = chat_pilot.hydrate_arguments(command, raw)
    args_hash = compute_args_hash(arguments.model_dump(mode="json", exclude_none=False))
    now = datetime.now(timezone.utc)
    deadline = build_accepted_chat_task_deadline(now - timedelta(hours=1) if expired else now)
    task = SimpleNamespace(request_id=f"request-{owner}", task_id=f"task-{owner}",
        thread_id=1 if owner == "a" else 2, turn_id=f"turn-{owner}", user_id=owner,
        origin="api:chat.complete", hosted_room_invocation=None, **deadline.to_dict())
    # This synthetic scope stands for an already authenticated route principal;
    # it does not prove HTTP authentication or queue admission end to end.
    account = ordinary_chat_acceptance_account(task, RequestUserScope(user_id=owner, account_id=owner))
    create_chat_completion_attempt(db, request_id=task.request_id, backend_task_id=task.task_id,
        thread_id=task.thread_id, turn_id=task.turn_id, deadline_snapshot=deadline,
        turn_lock_token="synthetic-lock", accepted_account_id=None if legacy else account)
    freeze_chat_tool_decision(db, request_id=task.request_id, backend_task_id=task.task_id,
        thread_id=task.thread_id, turn_id=task.turn_id, account_id=owner,
        command_id=command, args_hash=args_hash)
    if acknowledged:
        mark_chat_completion_attempt_accepted(db, backend_task_id=task.task_id)
    return task, command, args_hash


def resolve(db, state):
    task, command, args_hash = state
    return resolve_accepted_chat_account(db, task, command_id=command, args_hash=args_hash)


@pytest.mark.parametrize("provider", ["notion", "github"])
def test_real_rows_resolve_original_owner_with_exact_command_arguments(db, provider):
    state = accepted(db, provider=provider)
    binding = resolve(db, state)
    assert binding.account_id == "a"
    assert binding.request_id == state[0].request_id
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_account(db, state[0], command_id=state[1], args_hash="f" * 64)
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_account(db, state[0], command_id="op::notion_content_read", args_hash=state[2])


def test_publication_before_acknowledgement_denies_then_rereads(db):
    state = accepted(db, acknowledged=False)
    with pytest.raises(ChatAccountAcceptancePending):
        resolve(db, state)
    mark_chat_completion_attempt_accepted(db, backend_task_id=state[0].task_id)
    assert resolve(db, state).account_id == "a"


@pytest.mark.parametrize("mutation", ["task_owner", "thread_owner", "project_owner", "terminal", "cancelled", "preview_removed"])
def test_prior_binding_does_not_authorize_retry_after_current_state_changes(db, monkeypatch, mutation):
    state = accepted(db)
    original = resolve(db, state)
    if mutation == "task_owner":
        state[0].user_id = "b"
    elif mutation == "cancelled":
        monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: True)
    elif mutation == "preview_removed":
        monkeypatch.setattr("guardian.core.preview_access.is_private_preview", lambda: True)
        monkeypatch.setattr("guardian.core.preview_access.role_for_preview_email", lambda _: None)
    else:
        with db._sa_session() as session:
            if mutation == "thread_owner":
                session.get(ChatThread, 1).user_id = "b"
            elif mutation == "project_owner":
                session.add(Project(id=10, name="B", user_id="b"))
                session.flush()
                session.get(ChatThread, 1).project_id = 10
            else:
                session.get(ChatCompletionAttempt, state[0].request_id).terminal_event_type = "task.cancelled"
    assert original.account_id == "a"  # Old Python value is only old evidence.
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(db, state)


@pytest.mark.parametrize("legacy,expired", [(True, False), (False, True)])
def test_legacy_and_expired_rows_do_not_acquire_authority(db, legacy, expired):
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve(db, accepted(db, legacy=legacy, expired=expired))


def test_postgres_prevents_reassigning_original_account_custody(db):
    state = accepted(db)
    with pytest.raises(IntegrityError):
        with db._sa_session() as session:
            session.get(ChatCompletionAttempt, state[0].request_id).accepted_account_id = "b"
    assert resolve(db, state).account_id == "a"


def test_parallel_and_sequential_worker_lookups_do_not_share_account_context(db):
    a, b = accepted(db), accepted(db, "b")
    states = [a, b, a, b, b, a]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda state: resolve(db, state).account_id, states))
    assert results == ["a", "b", "a", "b", "b", "a"]
    assert resolve(db, a).account_id == "a"


@pytest.mark.parametrize("provider", ["notion", "github"])
def test_valid_custody_is_not_connection_permission_after_disconnect(db, provider):
    state = accepted(db, provider=provider)
    flow = oauth_store.begin_flow(db, "a", provider, "https://synthetic.invalid/callback", browser_binding="synthetic-browser")
    consumed = oauth_store.consume_flow(db, provider, flow.state, browser_binding="synthetic-browser")
    assert oauth_store.complete_flow(db, consumed, "synthetic-access", expires_in=3600)
    assert oauth_store.credential(db, "a", provider) is not None
    assert oauth_store.credential(db, "b", provider) is None
    assert resolve(db, state).account_id == "a"
    assert oauth_store.disconnect(db, "a", provider)
    assert oauth_store.credential(db, "a", provider) is None
    # This intentional separation proves why custody alone cannot enable dispatch.
    assert resolve(db, state).account_id == "a"
