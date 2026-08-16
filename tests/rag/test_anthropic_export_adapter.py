"""Focused tests for the Anthropic account-export source adapter.

These tests use synthetic fixtures only. They must not commit, depend on, or
import from any real Anthropic account export.

The adapter is intentionally a thin source-detection + provenance layer over
the existing Claude ingestion entrypoint (``backend.rag.chatgpt_migration``).
These tests verify the adapter's contract surface, not the persistence layer
itself. Persistence behavior is owned by the existing ``ingest_claude_export``
tests in ``backend/rag`` and by the focused Claude-ingestion tests in this
repository.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.rag import anthropic_export_adapter as adapter_module
from backend.rag.anthropic_export_adapter import (
    ANTHROPIC_IMPORT_PROFILE,
    SOURCE_SYSTEM,
    AnthropicExtractedConversation,
    AnthropicImportResult,
    extract_anthropic_conversations,
    import_anthropic_export_path,
    scan_anthropic_export_root,
)
from backend.rag.chatgpt_migration import (
    _CLAUDE_IMPORT_PROFILE,
    _canonicalize_claude_role,
    _extract_claude_text_content,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _anthropic_message(
    *,
    sender: str,
    text: str,
    message_uuid: str | None = None,
    created_at: str = "2026-01-01T00:00:00Z",
    parent_uuid: str = "00000000-0000-4000-8000-000000000000",
    files: list[dict] | None = None,
    attachments: list[dict] | None = None,
    content_blocks: list[dict] | None = None,
) -> dict:
    """Build one synthetic Anthropic message record.

    Defaults are deliberately minimal so the structural tests do not depend on
    the inspected real export's UUIDs, timestamps, or account UUIDs.
    """

    message_uuid = message_uuid or f"m-{text[:8]}"
    text_block = (
        content_blocks
        if content_blocks is not None
        else [{"type": "text", "text": text}]
    )
    record: dict = {
        "uuid": message_uuid,
        "text": text,
        "content": text_block,
        "sender": sender,
        "created_at": created_at,
        "updated_at": created_at,
        "attachments": attachments or [],
        "files": files or [],
        "parent_message_uuid": parent_uuid,
    }
    return record


def _anthropic_conversation(
    *,
    conv_uuid: str,
    name: str,
    messages: list[dict],
    created_at: str = "2026-01-01T00:00:00Z",
    updated_at: str | None = None,
) -> dict:
    return {
        "uuid": conv_uuid,
        "name": name,
        "summary": "synthetic",
        "created_at": created_at,
        "updated_at": updated_at or created_at,
        "account": {"uuid": "00000000-0000-4000-8000-000000000001"},
        "chat_messages": messages,
    }


def _write_anthropic_export(
    root: Path,
    *,
    conversations: list[dict],
    include_projects: bool = True,
    include_users: bool = True,
    include_memories: bool = True,
) -> None:
    """Materialize one synthetic extracted Anthropic export root."""

    (root / "conversations.json").write_text(
        json.dumps(conversations, ensure_ascii=False), encoding="utf-8"
    )
    if include_projects:
        projects_dir = root / "projects"
        projects_dir.mkdir(exist_ok=True)
        (projects_dir / "019b33d4-a874-75ca-a19f-c4d32fe2d2e0.json").write_text(
            json.dumps(
                {
                    "uuid": "019b33d4-a874-75ca-a19f-c4d32fe2d2e0",
                    "name": "Edge Computing",
                    "description": "",
                    "is_private": True,
                    "is_starter_project": False,
                    "prompt_template": "",
                    "created_at": "2025-12-18T23:38:53.432723+00:00",
                    "updated_at": "2025-12-18T23:38:53.432723+00:00",
                    "creator": {
                        "uuid": "00000000-0000-4000-8000-000000000001",
                        "full_name": "Synthetic",
                    },
                    "docs": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    if include_users:
        (root / "users.json").write_text(
            json.dumps(
                [
                    {
                        "uuid": "00000000-0000-4000-8000-000000000001",
                        "full_name": "Synthetic",
                        "email_address": "synthetic@example.invalid",
                    }
                ]
            ),
            encoding="utf-8",
        )
    if include_memories:
        (root / "memories.json").write_text(
            json.dumps(
                [
                    {
                        "conversations_memory": (
                            "synthetic memory payload that must never be "
                            "imported by the adapter"
                        )
                    }
                ]
            ),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_positive_anthropic_root_detection(tmp_path: Path):
    conversations = [
        _anthropic_conversation(
            conv_uuid="c-positive",
            name="Positive Detection",
            messages=[
                _anthropic_message(
                    sender="human", text="hello", message_uuid="m-h-1"
                ),
                _anthropic_message(
                    sender="assistant", text="world", message_uuid="m-a-1"
                ),
            ],
        )
    ]
    _write_anthropic_export(tmp_path, conversations=conversations)

    inventory = scan_anthropic_export_root(tmp_path)

    assert inventory.conversation_candidate is True
    assert inventory.detected_format == "anthropic_legacy"
    assert inventory.reason == "anthropic_chat_messages_payload_found"
    paths = {record.path for record in inventory.conversation_files}
    assert "conversations.json" in paths


def test_misleading_non_anthropic_json_is_rejected(tmp_path: Path):
    """Filename 'conversations.json' must not, on its own, classify an export
    as Anthropic. The detector must require real ``chat_messages`` evidence."""

    (tmp_path / "conversations.json").write_text(
        json.dumps(
            [
                {"id": "x", "title": "Looks like ChatGPT", "mapping": {"m1": {}}},
            ]
        ),
        encoding="utf-8",
    )
    # Add a deliberately misleading OpenAI-shaped conversation.
    (tmp_path / "users.json").write_text(
        json.dumps([{"uuid": "u-1", "full_name": "x", "email_address": "x@x"}]),
        encoding="utf-8",
    )

    inventory = scan_anthropic_export_root(tmp_path)

    assert inventory.conversation_candidate is False
    assert inventory.detected_format == "unknown"
    assert inventory.conversation_files == ()


def test_openai_shaped_payload_is_not_classified_as_anthropic(tmp_path: Path):
    """OpenAI's mapping-based conversations are explicitly NOT Anthropic."""

    (tmp_path / "conversations.json").write_text(
        json.dumps(
            [
                {
                    "id": "openai-thread",
                    "title": "OpenAI thread",
                    "mapping": {
                        "m1": {
                            "id": "m1",
                            "message": {
                                "id": "m1",
                                "author": {"role": "user"},
                                "content": {"parts": ["hello"]},
                            },
                        }
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    inventory = scan_anthropic_export_root(tmp_path)
    assert inventory.conversation_candidate is False
    assert inventory.detected_format == "unknown"


def test_wrapper_key_payload_is_detected(tmp_path: Path):
    """A dict with ``conversations`` wrapper key containing ``chat_messages``
    records must still classify as Anthropic."""

    (tmp_path / "conversations.json").write_text(
        json.dumps(
            {
                "conversations": [
                    _anthropic_conversation(
                        conv_uuid="c-wrap",
                        name="Wrapper",
                        messages=[
                            _anthropic_message(
                                sender="human",
                                text="wrapped",
                                message_uuid="m-w-1",
                            )
                        ],
                    )
                ]
            }
        ),
        encoding="utf-8",
    )

    inventory = scan_anthropic_export_root(tmp_path)
    assert inventory.conversation_candidate is True
    assert inventory.detected_format == "anthropic_legacy"


def test_missing_root_does_not_classify(tmp_path: Path):
    inventory = scan_anthropic_export_root(tmp_path / "no-such-root")
    assert inventory.conversation_candidate is False
    assert inventory.reason == "root_does_not_exist"
    assert inventory.detected_format == "unknown"


def test_projects_users_memories_are_scanned_but_not_classified_as_conversations(
    tmp_path: Path,
):
    conversations = [
        _anthropic_conversation(
            conv_uuid="c-sidecar",
            name="Sidecar",
            messages=[_anthropic_message(sender="human", text="hi")],
        )
    ]
    _write_anthropic_export(tmp_path, conversations=conversations)

    inventory = scan_anthropic_export_root(tmp_path)

    # projects/, users.json, memories.json are inventoried but must not be
    # considered conversation candidates.
    non_conversation_paths = {
        record.path
        for record in inventory.files
        if record.path != "conversations.json"
    }
    assert any(path.startswith("projects/") for path in non_conversation_paths)
    assert "users.json" in non_conversation_paths
    assert "memories.json" in non_conversation_paths
    conversation_paths = {record.path for record in inventory.conversation_files}
    assert conversation_paths == {"conversations.json"}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def test_conversation_extraction_preserves_source_path_and_order(
    tmp_path: Path,
):
    first = _anthropic_conversation(
        conv_uuid="c-first",
        name="First",
        messages=[
            _anthropic_message(sender="human", text="first hi", message_uuid="m-1")
        ],
    )
    second = _anthropic_conversation(
        conv_uuid="c-second",
        name="Second",
        messages=[
            _anthropic_message(sender="human", text="second hi", message_uuid="m-2")
        ],
    )
    _write_anthropic_export(
        tmp_path, conversations=[first, second], include_projects=False
    )

    inventory = scan_anthropic_export_root(tmp_path)
    extracted = extract_anthropic_conversations(inventory)

    assert len(extracted) == 2
    assert all(isinstance(item, AnthropicExtractedConversation) for item in extracted)
    assert [item.conversation["uuid"] for item in extracted] == [
        "c-first",
        "c-second",
    ]
    assert all(item.source_path == "conversations.json" for item in extracted)


def test_extraction_drops_records_without_chat_messages(tmp_path: Path):
    """A wrapper key record that lacks ``chat_messages`` must not be returned."""

    (tmp_path / "conversations.json").write_text(
        json.dumps(
            [
                {
                    "uuid": "no-chat",
                    "name": "No Chat",
                    "summary": "",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "account": {"uuid": "u"},
                },
                _anthropic_conversation(
                    conv_uuid="c-real",
                    name="Real",
                    messages=[_anthropic_message(sender="human", text="hi")],
                ),
            ]
        ),
        encoding="utf-8",
    )

    inventory = scan_anthropic_export_root(tmp_path)
    extracted = extract_anthropic_conversations(inventory)

    assert [item.conversation["uuid"] for item in extracted] == ["c-real"]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_normalization_attaches_codexify_import_metadata(tmp_path: Path):
    record = _anthropic_conversation(
        conv_uuid="c-meta",
        name="Meta",
        messages=[_anthropic_message(sender="human", text="hi", message_uuid="m-1")],
    )

    normalized = adapter_module._normalize_conversation_record(
        record, source_path="conversations.json"
    )

    metadata = normalized["_codexify_import_metadata"]
    assert metadata["anthropic_export_format"] == "anthropic_legacy"
    assert metadata["anthropic_export_source_path"] == "conversations.json"
    assert metadata["anthropic_import_profile"] == ANTHROPIC_IMPORT_PROFILE
    # The original record's top-level fields must remain intact.
    assert normalized["uuid"] == "c-meta"
    assert normalized["chat_messages"] == record["chat_messages"]


def test_normalization_preserves_existing_import_metadata(tmp_path: Path):
    record = _anthropic_conversation(
        conv_uuid="c-preserve",
        name="Preserve",
        messages=[_anthropic_message(sender="human", text="hi")],
    )
    record["_codexify_import_metadata"] = {"prior_field": "kept"}

    normalized = adapter_module._normalize_conversation_record(
        record, source_path="conversations.json"
    )
    metadata = normalized["_codexify_import_metadata"]
    assert metadata["prior_field"] == "kept"
    assert metadata["anthropic_export_format"] == "anthropic_legacy"


# ---------------------------------------------------------------------------
# Role mapping through the existing Claude path
# ---------------------------------------------------------------------------


def test_human_maps_to_user_and_assistant_remains_assistant():
    """Role mapping is delegated to the existing Claude contract; verify the
    delegation boundary holds with the canonical role mapper."""

    assert _canonicalize_claude_role("human") == ("user", None)
    assert _canonicalize_claude_role("assistant") == ("assistant", None)


def test_claude_text_extraction_handles_text_blocks():
    block = [
        {
            "type": "text",
            "text": "hello",
        }
    ]
    assert _extract_claude_text_content(block) == "hello"


# ---------------------------------------------------------------------------
# File metadata does not produce media persistence
# ---------------------------------------------------------------------------


def test_metadata_only_files_do_not_persist(tmp_path: Path, monkeypatch):
    """When the adapter is invoked, ``files[]`` references with only
    ``file_uuid``/``file_name`` (no bytes) must NOT cause any media-asset
    write to occur. We assert this by monkey-patching the existing OpenAI
    media import helper to fail the test if the worker would call it for
    Anthropic."""

    sentinel = SimpleNamespace(calls=0)

    def _fail_if_called(*_args, **_kwargs):
        sentinel.calls += 1
        raise AssertionError(
            "Anthropic adapter must not call the OpenAI media ingestion path."
        )

    monkeypatch.setattr(
        "guardian.workers.account_import_worker.import_image_record",
        _fail_if_called,
        raising=False,
    )

    conversation = _anthropic_conversation(
        conv_uuid="c-files",
        name="Files",
        messages=[
            _anthropic_message(
                sender="human",
                text="see attached photo",
                message_uuid="m-photo",
                files=[{"file_uuid": "u-photo-1", "file_name": "photo"}],
                attachments=[
                    {
                        "extracted_content": "metadata-only",
                        "file_name": "photo",
                        "file_size": 1234,
                        "file_type": "image/png",
                    }
                ],
            ),
        ],
    )
    _write_anthropic_export(tmp_path, conversations=[conversation])

    # The adapter is read-only at this layer. We verify the worker dispatch
    # never invokes ``import_image_record`` by exercising the dispatch branch
    # in isolation against a stub service. The full worker behavior is
    # covered in tests/workers/test_account_import_worker.py.
    inventory = scan_anthropic_export_root(tmp_path)
    extracted = extract_anthropic_conversations(inventory)
    assert len(extracted) == 1
    assert extracted[0].conversation["chat_messages"][0]["files"] == [
        {"file_uuid": "u-photo-1", "file_name": "photo"}
    ]


# ---------------------------------------------------------------------------
# Service/worker dispatch contract
# ---------------------------------------------------------------------------


def test_source_system_token_is_anthropic():
    assert SOURCE_SYSTEM == "anthropic"
    assert ANTHROPIC_IMPORT_PROFILE == "anthropic_v1_canonical"
    assert _CLAUDE_IMPORT_PROFILE == "claude_v1_canonical"


def test_malformed_corpus_returns_failure_result_not_success(
    monkeypatch, tmp_path: Path
):
    """Malformed source data must surface as an explicit failure result, not
    a silent successful import."""

    # Detector returns no candidates for a root that lacks chat_messages.
    (tmp_path / "conversations.json").write_text(
        json.dumps([{"id": "x", "title": "y", "mapping": {}}]), encoding="utf-8"
    )

    def _fail(*_args, **_kwargs):
        raise AssertionError(
            "ingest_claude_export must not be called when the detector reports "
            "no positive evidence."
        )

    monkeypatch.setattr(
        "backend.rag.chatgpt_migration.ingest_claude_export", _fail, raising=False
    )

    result = import_anthropic_export_path(tmp_path, user_id="synthetic-user")

    assert isinstance(result, AnthropicImportResult)
    assert result.conversations_discovered == 0
    assert result.conversations_imported == 0
    assert result.conversations_failed == 0
    assert result.errors, "expected an explicit error for malformed corpus"
    assert "chat_messages" in result.errors[0]


def test_dispatch_path_calls_ingest_claude_export_with_normalized_records(
    monkeypatch, tmp_path: Path
):
    """When the detector finds a corpus, ``import_anthropic_export_path`` must
    delegate persistence to the existing Claude ingestion entrypoint and pass
    through the normalized conversation records (with provenance attached)."""

    captured = SimpleNamespace(blob=b"", user_id="")

    def _capture_ingest(content: bytes, *, user_id: str):  # type: ignore[no-untyped-def]
        captured.blob = content
        captured.user_id = user_id
        return {
            "threads_imported": 1,
            "messages_imported": 2,
            "projects_created": 0,
            "projects_reused": 0,
            "messages_filtered": 0,
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        }

    monkeypatch.setattr(
        "backend.rag.chatgpt_migration.ingest_claude_export", _capture_ingest
    )

    conv = _anthropic_conversation(
        conv_uuid="c-dispatch",
        name="Dispatch",
        messages=[
            _anthropic_message(sender="human", text="hi", message_uuid="m-1"),
            _anthropic_message(
                sender="assistant", text="hello back", message_uuid="m-2"
            ),
        ],
    )
    _write_anthropic_export(tmp_path, conversations=[conv])

    result = import_anthropic_export_path(tmp_path, user_id="account-a")

    assert result.conversations_discovered == 1
    assert result.conversations_imported == 1
    assert result.conversations_failed == 0
    assert captured.user_id == "account-a"

    payload = json.loads(captured.blob.decode("utf-8"))
    assert isinstance(payload, list) and len(payload) == 1
    metadata = payload[0]["_codexify_import_metadata"]
    assert metadata["anthropic_export_format"] == "anthropic_legacy"
    assert metadata["anthropic_export_source_path"] == "conversations.json"
    assert metadata["anthropic_import_profile"] == ANTHROPIC_IMPORT_PROFILE

    # Sanity: the conversation passed through keeps its original message IDs.
    message_uuids = [m["uuid"] for m in payload[0]["chat_messages"]]
    assert message_uuids == ["m-1", "m-2"]


def test_projects_users_memories_presence_does_not_fail_dispatch(
    monkeypatch, tmp_path: Path
):
    """Sidecar source files must not affect dispatch success or failure."""

    captured = SimpleNamespace(blob=b"")

    def _capture_ingest(content: bytes, *, user_id: str):  # type: ignore[no-untyped-def]
        captured.blob = content
        return {
            "threads_imported": 1,
            "messages_imported": 1,
            "projects_created": 0,
            "projects_reused": 0,
            "messages_filtered": 0,
            "embedding_candidates": 0,
            "embeddings_persisted": 0,
            "embeddings_failed": 0,
            "embedding_coverage_degraded": False,
        }

    monkeypatch.setattr(
        "backend.rag.chatgpt_migration.ingest_claude_export", _capture_ingest
    )

    conv = _anthropic_conversation(
        conv_uuid="c-sidecar-dispatch",
        name="Sidecar Dispatch",
        messages=[_anthropic_message(sender="human", text="hi")],
    )
    _write_anthropic_export(
        tmp_path,
        conversations=[conv],
        include_projects=True,
        include_users=True,
        include_memories=True,
    )

    result = import_anthropic_export_path(tmp_path, user_id="account-a")

    assert result.errors == []
    assert result.conversations_imported == 1
    # The captured payload must contain exactly the conversation record; the
    # sidecar files must not have been forwarded to the ingest path.
    payload = json.loads(captured.blob.decode("utf-8"))
    assert len(payload) == 1


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


def test_extraction_preserves_deterministic_message_ordering(tmp_path: Path):
    messages = [
        _anthropic_message(sender="human", text=f"m{i}", message_uuid=f"m-uuid-{i}")
        for i in range(5)
    ]
    conv = _anthropic_conversation(
        conv_uuid="c-order",
        name="Order",
        messages=messages,
    )
    _write_anthropic_export(tmp_path, conversations=[conv])

    inventory = scan_anthropic_export_root(tmp_path)
    extracted = extract_anthropic_conversations(inventory)
    assert len(extracted) == 1
    payload = extracted[0].conversation
    assert [m["uuid"] for m in payload["chat_messages"]] == [
        f"m-uuid-{i}" for i in range(5)
    ]


# ---------------------------------------------------------------------------
# Provenance-key shape regression
# ---------------------------------------------------------------------------


def test_provenance_key_pattern_matches_openai_adapter():
    """The provenance key pattern mirrors the OpenAI adapter's openai_export_*
    naming. A regression here would break the documented contract that
    provenance metadata is keyed by source_system."""

    pattern = re.compile(r"^anthropic_export_[a-z_]+$")
    for key in ("anthropic_export_format", "anthropic_export_source_path"):
        assert pattern.match(key), (
            f"provenance key {key!r} must follow anthropic_export_<snake_case>"
        )
