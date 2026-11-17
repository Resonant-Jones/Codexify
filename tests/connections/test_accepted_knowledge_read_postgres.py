"""Real PostgreSQL proof for the unwired ADR-112 authority fence.

Uses the same guarded disposable fixture as the custody prerequisite tests.
No provider requests, real credentials or runtime dispatch are involved.
"""

import json
import time

import pytest

from guardian.command_bus import accepted_knowledge_read as reads
from guardian.command_bus.contracts import InvokeArguments
from guardian.connections import chat_pilot, oauth_store
from guardian.db.models import ChatCompletionAttempt, KnowledgeOAuthCredential
from tests.connections import test_accepted_chat_custody_postgres as custody

# Reuse the guarded fixture objects without importing names shadowed by pytest
# fixture parameters. No test can fall back to an ambient application DSN.
accepted = custody.accepted
db = custody.db
engine = custody.engine


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH", "1")


def connect(db, owner="a", provider="notion"):
    flow = oauth_store.begin_flow(
        db,
        owner,
        provider,
        "https://synthetic.invalid/callback",
        repositories=["example/selected"] if provider == "github" else None,
        browser_binding="synthetic-browser",
    )
    consumed = oauth_store.consume_flow(
        db, provider, flow.state, browser_binding="synthetic-browser"
    )
    assert oauth_store.complete_flow(
        db, consumed, f"synthetic-access-{owner}", "synthetic-refresh", expires_in=3600
    )


def prepare(db, owner="a", provider="notion", *, acknowledged=True):
    task, command, _ = accepted(db, owner, provider, acknowledged=acknowledged)
    raw = {"query": "synthetic"}
    if provider == "github":
        raw["repository"] = "example/selected"
    return task, reads.prepare_accepted_knowledge_read(
        db,
        task,
        command_id=command,
        arguments=chat_pilot.hydrate_arguments(command, raw),
    )


def run_for(fence):
    lineage = fence.lineage()
    return {
        "auth_subject": lineage["account_id"],
        "command_id": lineage["command_id"],
        "args_hash": lineage["args_hash"],
        "idempotency_key": fence.idempotency_key(),
    }


@pytest.mark.parametrize("provider", ["github", "notion"])
def test_metadata_replay_check_never_decrypts_and_io_is_just_in_time(
    db, monkeypatch, provider
):
    connect(db, provider=provider)
    real_decrypt = oauth_store.decrypt_token
    monkeypatch.setattr(
        oauth_store, "decrypt_token", lambda _: pytest.fail("metadata must not decrypt")
    )
    _, fence = prepare(db, provider=provider)
    fence.validate_replay(run_for(fence))
    assert "synthetic-access" not in json.dumps(fence.lineage()) + repr(fence)
    monkeypatch.setattr(oauth_store, "decrypt_token", real_decrypt)
    assert fence.credential_for_io().access_token == "synthetic-access-a"


@pytest.mark.parametrize(
    "mutation",
    [
        "disconnect",
        "refresh_claim",
        "expired",
        "reconnect",
        "terminal",
        "cancelled",
        "feature_off",
    ],
)
def test_each_boundary_refuses_revoked_or_ineligible_work(db, monkeypatch, mutation):
    connect(db)
    task, fence = prepare(db)
    replay = run_for(fence)
    if mutation == "disconnect":
        oauth_store.disconnect(db, "a", "notion")
    elif mutation == "refresh_claim":
        assert oauth_store.claim_refresh(db, "a", "notion") is not None
    elif mutation == "reconnect":
        connect(db)
    elif mutation == "cancelled":
        monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: True)
    elif mutation == "feature_off":
        monkeypatch.delenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH")
    else:
        with db.get_session() as session:
            if mutation == "expired":
                row = (
                    session.query(KnowledgeOAuthCredential)
                    .filter_by(user_id="a", provider="notion")
                    .one()
                )
                row.expires_at = time.time() - 1
            else:
                session.get(
                    ChatCompletionAttempt, task.request_id
                ).terminal_event_type = "task.cancelled"
            session.commit()
    for operation in [
        fence.revalidate,
        fence.credential_for_io,
        fence.lineage,
        lambda: fence.validate_replay(replay),
    ]:
        with pytest.raises(
            reads.AcceptedKnowledgeReadUnavailable,
            match="^accepted_knowledge_read_unavailable$",
        ):
            operation()


def test_repository_reselection_changes_generation_and_replay_identity(db):
    connect(db, provider="github")
    task, fence = prepare(db, provider="github")
    old_run = run_for(fence)
    generation = fence.lineage()["connection_generation"]
    assert oauth_store.save_repositories(
        db, "a", "github", generation, "123", ["example/selected", "example/second"]
    )
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        fence.validate_replay(old_run)
    fresh = reads.prepare_accepted_knowledge_read(
        db,
        task,
        command_id="op::github_content_search",
        arguments=chat_pilot.hydrate_arguments(
            "op::github_content_search",
            {"query": "synthetic", "repository": "example/selected"},
        ),
    )
    assert fresh.idempotency_key() != old_run["idempotency_key"]
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        fresh.validate_replay(old_run)


def test_removed_repository_denies_new_attempt(db):
    connect(db, provider="github")
    task, fence = prepare(db, provider="github")
    assert oauth_store.save_repositories(
        db,
        "a",
        "github",
        fence.lineage()["connection_generation"],
        "123",
        ["example/other"],
    )
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        reads.prepare_accepted_knowledge_read(
            db,
            task,
            command_id="op::github_content_search",
            arguments=chat_pilot.hydrate_arguments(
                "op::github_content_search",
                {"query": "synthetic", "repository": "example/selected"},
            ),
        )


def test_disconnect_during_credential_resolution_discards_snapshot(db, monkeypatch):
    connect(db)
    _, fence = prepare(db)
    original = oauth_store.credential

    def raced(*args):
        snapshot = original(*args)
        oauth_store.disconnect(db, "a", "notion")
        return snapshot

    monkeypatch.setattr(oauth_store, "credential", raced)
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        fence.credential_for_io()


def test_revalidate_after_inflight_revocation_denies_result_publication(db):
    connect(db)
    _, fence = prepare(db)
    snapshot = fence.credential_for_io()
    assert snapshot.access_token
    oauth_store.disconnect(db, "a", "notion")
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        fence.revalidate()
    # This proves the post-I/O check, not physical cancellation of provider I/O.


@pytest.mark.parametrize(
    "field", ["auth_subject", "command_id", "args_hash", "idempotency_key"]
)
def test_replay_cannot_rebind_account_command_arguments_or_generation(db, field):
    connect(db)
    _, fence = prepare(db)
    replay = run_for(fence)
    replay[field] = "foreign-value"
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        fence.validate_replay(replay)


def test_sequential_accounts_keep_credentials_and_replay_separate(db):
    for owner in ["a", "b"]:
        connect(db, owner)
    task_a, a = prepare(db, "a")
    _, b = prepare(db, "b")
    assert a.credential_for_io().access_token == "synthetic-access-a"
    assert b.credential_for_io().access_token == "synthetic-access-b"
    assert a.credential_for_io().access_token == "synthetic-access-a"
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        b.validate_replay(run_for(a))
    task_a.user_id = "b"  # Caller mutation cannot replace frozen evidence.
    assert a.revalidate().account_id == "a"


def test_monotonic_budget_cannot_be_extended_by_wall_clock_change(db, monkeypatch):
    connect(db)
    _, fence = prepare(db)
    monkeypatch.setattr(reads.time, "monotonic", lambda: fence._monotonic_deadline + 1)
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        fence.credential_for_io()


def test_argument_copies_cannot_mutate_the_accepted_execution(db):
    connect(db)
    task, command, _ = accepted(db)
    arguments = InvokeArguments(query={"query": "synthetic"})
    fence = reads.prepare_accepted_knowledge_read(
        db, task, command_id=command, arguments=arguments
    )
    arguments.query["query"] = "caller-mutated"
    copied = fence.arguments()
    assert copied.query == {"query": "synthetic"}
    copied.query["query"] = "adapter-mutated"
    assert fence.arguments().query == {"query": "synthetic"}


def test_unacknowledged_acceptance_remains_distinct_pending_refusal(db):
    connect(db)
    with pytest.raises(reads.ChatAccountAcceptancePending):
        prepare(db, acknowledged=False)


def test_no_connection_means_no_legacy_or_refresh_fallback(db, monkeypatch):
    monkeypatch.setattr(
        "guardian.connections.knowledge_oauth.credential",
        lambda *a: pytest.fail("no network refresh"),
    )
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        prepare(db)


@pytest.mark.parametrize(
    "change", ["header", "body", "unknown", "query_extra", "wrong_query"]
)
def test_noncanonical_arguments_fail_before_any_credential_read(
    db, monkeypatch, change
):
    task, command, _ = accepted(db)
    arguments = InvokeArguments(query={"query": "synthetic"})
    if change == "header":
        arguments.headers["Authorization"] = "synthetic-caller-secret"
    elif change == "body":
        arguments.body = {"account_id": "b"}
    elif change == "unknown":
        command = "op::arbitrary_operation"
    elif change == "query_extra":
        arguments.query["account_id"] = "b"
    else:
        arguments.query["query"] = "changed"
    monkeypatch.setattr(
        oauth_store,
        "read_grant",
        lambda *a: pytest.fail("deny before connection lookup"),
    )
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        reads.prepare_accepted_knowledge_read(
            db, task, command_id=command, arguments=arguments
        )
