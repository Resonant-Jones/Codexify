"""Always-on boundary tests; real canonical-row proof is in the PG module."""

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from guardian.command_bus import accepted_knowledge_read as reads
from guardian.command_bus.contracts import InvokeArguments
from guardian.command_bus.redaction_policy import compute_args_hash
from guardian.connections import chat_pilot, oauth_store
from guardian.core.chat_account_custody import AcceptedChatAccountBinding
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline


def fixture(monkeypatch, command, raw):
    arguments = chat_pilot.hydrate_arguments(command, raw)
    digest = compute_args_hash(arguments.model_dump(mode="json", exclude_none=False))
    task = SimpleNamespace(
        request_id="request-a",
        task_id="task-a",
        thread_id=1,
        turn_id="turn-a",
        user_id="a",
        origin="api:chat.complete",
        hosted_room_invocation=None,
        **build_accepted_chat_task_deadline(datetime.now(timezone.utc)).to_dict(),
    )
    binding = AcceptedChatAccountBinding(
        "a", "request-a", "task-a", 1, "turn-a", "tool-a", command, digest
    )
    provider = chat_pilot.COMMANDS[command][0]
    grant = oauth_store.ReadGrant(
        "a",
        provider,
        "generation-a",
        None,
        ("example/selected",) if provider == "github" else (),
    )
    observed = []

    def canonical(db, evidence, *, command_id, args_hash):
        observed.append((command_id, args_hash))
        assert command_id == command and args_hash == digest
        return binding

    monkeypatch.setenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH", "1")
    monkeypatch.setattr(reads, "resolve_accepted_chat_account", canonical)
    monkeypatch.setattr(oauth_store, "read_grant", lambda *a: grant)
    monkeypatch.setattr(
        oauth_store,
        "credential",
        lambda *a: pytest.fail("metadata must not access tokens"),
    )
    return task, arguments, grant, observed


@pytest.mark.parametrize(
    "command,raw",
    [
        ("op::notion_content_search", {"query": "synthetic"}),
        (
            "op::notion_content_read",
            {"object_id": "11111111-1111-1111-1111-111111111111"},
        ),
        (
            "op::github_content_search",
            {"query": "synthetic", "repository": "example/selected"},
        ),
        ("op::github_content_read", {"repository": "example/selected", "number": 1}),
    ],
)
def test_all_four_commands_preserve_exact_hash_and_safe_lineage(
    monkeypatch, command, raw
):
    task, args, _, observed = fixture(monkeypatch, command, raw)
    fence = reads.prepare_accepted_knowledge_read(
        object(), task, command_id=command, arguments=args
    )
    before = len(observed)
    assert fence.arguments() == args
    assert 0 < fence.remaining_seconds() <= 720
    lineage = fence.lineage()
    fence.validate_replay(
        {
            "auth_subject": "a",
            "command_id": command,
            "args_hash": lineage["args_hash"],
            "idempotency_key": fence.idempotency_key(),
        }
    )
    assert len(observed) > before
    assert set(lineage) == {
        "account_id",
        "request_id",
        "backend_task_id",
        "thread_id",
        "turn_id",
        "tool_turn_id",
        "command_id",
        "args_hash",
        "connection_generation",
        "provider",
    }


@pytest.mark.parametrize(
    "change", ["missing", "owner", "provider", "generation", "expiry", "repositories"]
)
def test_current_connection_mismatch_refuses_without_decryption(monkeypatch, change):
    command = "op::github_content_search"
    task, args, grant, _ = fixture(
        monkeypatch, command, {"query": "synthetic", "repository": "example/selected"}
    )
    fence = reads.prepare_accepted_knowledge_read(
        object(), task, command_id=command, arguments=args
    )
    altered = {
        "missing": None,
        "owner": replace(grant, user_id="b"),
        "provider": replace(grant, provider="notion"),
        "generation": replace(grant, generation="new"),
        "expiry": replace(grant, expires_at=0),
        "repositories": replace(grant, repositories=("example/other",)),
    }[change]
    monkeypatch.setattr(oauth_store, "read_grant", lambda *a: altered)
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        fence.credential_for_io()


def test_storage_failure_is_bounded_without_exception_context(monkeypatch):
    command = "op::notion_content_search"
    task, args, _, _ = fixture(monkeypatch, command, {"query": "synthetic"})

    def broken(*a):
        raise RuntimeError("synthetic-sensitive-db-detail")

    monkeypatch.setattr(oauth_store, "read_grant", broken)
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable) as caught:
        reads.prepare_accepted_knowledge_read(
            object(), task, command_id=command, arguments=args
        )
    assert str(caught.value) == "accepted_knowledge_read_unavailable"
    assert caught.value.__suppress_context__


def test_unknown_command_never_resolves_account_or_connection(monkeypatch):
    monkeypatch.setattr(
        reads,
        "resolve_accepted_chat_account",
        lambda *a, **k: pytest.fail("no arbitrary command"),
    )
    with pytest.raises(reads.AcceptedKnowledgeReadUnavailable):
        reads.prepare_accepted_knowledge_read(
            object(), object(), command_id="op::write", arguments=InvokeArguments()
        )


def test_provider_expiry_bounds_transport_budget(monkeypatch):
    command = "op::notion_content_search"
    task, args, grant, _ = fixture(monkeypatch, command, {"query": "synthetic"})
    grant = replace(grant, expires_at=reads.time.time() + 5)
    monkeypatch.setattr(oauth_store, "read_grant", lambda *a: grant)
    fence = reads.prepare_accepted_knowledge_read(
        object(), task, command_id=command, arguments=args
    )
    assert 0 < fence.remaining_seconds() <= 5
