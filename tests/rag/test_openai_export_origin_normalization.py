"""Prove the canonical conversation-origin invariant for both import paths.

These tests verify that the importer's canonical writer (``_ingest_canonical_messages``
in ``backend.rag.chatgpt_migration``) stamps the canonical ``origin_system``
token on every created thread based on the legacy ``import_source`` product
label:

- ``import_source="chatgpt"`` -> ``origin_system="openai"``
- ``import_source="claude"``  -> ``origin_system="anthropic"``

They do NOT exercise the database. They prove that the canonical-mapping
contract is honored at the import seam, which is the layer that decides the
origin. The Postgres CHECK constraint and Alembic migration are verified
separately via the migration-graph integrity command in the proof surface.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from backend.rag.chatgpt_migration import (
    _CHATGPT_IMPORT_PROFILE,
    _CLAUDE_IMPORT_PROFILE,
    _ingest_canonical_messages,
)


class _RecordingChatlogDB:
    """Tiny chatlog facade that records every ``create_chat_thread`` call.

    The canonical writer is the only path we exercise here; we don't need
    a real Postgres round-trip to prove the canonical mapping contract.
    """

    def __init__(self) -> None:
        self.created: List[Dict[str, Any]] = []
        self.metadata_updates: List[Dict[str, Any]] = []
        self._next_message_id = 1000

    def create_chat_thread(self, **kwargs: Any) -> Dict[str, Any]:
        self.created.append(kwargs)
        # Return a minimal canonical-row stub so the writer proceeds.
        return {
            "id": len(self.created),
            "user_id": kwargs.get("user_id"),
            "title": kwargs.get("title", "imported"),
            "summary": kwargs.get("summary", ""),
            "project_id": kwargs.get("project_id"),
            "metadata": kwargs.get("metadata") or {},
            "active_profile_id": kwargs.get("active_profile_id"),
            "is_diary": False,
            "diary_mode": False,
            "exclude_from_identity": False,
            "modeling_excluded": False,
            "thread_config": None,
            "origin_system": kwargs.get("origin_system", "codexify"),
            "created_at": "2026-08-14T00:00:00Z",
            "updated_at": "2026-08-14T00:00:00Z",
        }

    def update_thread_metadata(self, *args: Any, **kwargs: Any) -> None:
        return None

    def create_message(
        self, *args: Any, **kwargs: Any
    ) -> int:
        # The canonical writer persists message rows via ``create_message``;
        # we only need to return a stable integer for the helper to continue.
        self._next_message_id += 1
        return self._next_message_id

    def write_audit_log(self, *args: Any, **kwargs: Any) -> None:
        return None


def _make_message(role: str, content: str) -> Dict[str, Any]:
    return {
        "role": role,
        "content": content,
        "source_thread_id": "src-1",
        "source_message_id": f"m-{role}",
        "turn_index": 0,
        "source_created_at": __import__("datetime").datetime(2026, 1, 1),
        "imported_at": __import__("datetime").datetime(2026, 8, 14),
        "raw_role": role,
        "raw_message": {"text": content},
        "origin": "import",
        "era": "pre_codexify",
    }


@pytest.fixture
def chatlog_db() -> _RecordingChatlogDB:
    return _RecordingChatlogDB()


# ---------------------------------------------------------------------------
# ChatGPT/OpenAI path -> openai
# ---------------------------------------------------------------------------


def test_chatgpt_import_stamps_openai_origin(chatlog_db):
    threads, messages = _ingest_canonical_messages(
        chatlog_db=chatlog_db,
        user_id="account-a",
        title="Imported ChatGPT",
        thread_summary="Imported from ChatGPT",
        import_source="chatgpt",
        import_profile=_CHATGPT_IMPORT_PROFILE,
        source_thread_id="src-chatgpt-1",
        messages=[_make_message("user", "hello")],
        imports_project_id=10,
        import_grouping_metadata={},
        pending_embed_items=[],
        pending_embed_message_ids=[],
        filtered_count=0,
        filtered_reasons={},
        embedding_mode="enqueue",
        disable_personal_facts=False,
    )
    assert threads == 1
    assert messages == 1
    assert len(chatlog_db.created) == 1
    canonical_kwargs = chatlog_db.created[0]
    assert canonical_kwargs["origin_system"] == "openai"


# ---------------------------------------------------------------------------
# Anthropic/Claude path -> anthropic
# ---------------------------------------------------------------------------


def test_anthropic_import_stamps_anthropic_origin(chatlog_db):
    threads, messages = _ingest_canonical_messages(
        chatlog_db=chatlog_db,
        user_id="account-a",
        title="Imported Claude",
        thread_summary="Imported from Claude",
        import_source="claude",
        import_profile=_CLAUDE_IMPORT_PROFILE,
        source_thread_id="src-claude-1",
        messages=[_make_message("user", "hello")],
        imports_project_id=10,
        import_grouping_metadata={},
        pending_embed_items=[],
        pending_embed_message_ids=[],
        filtered_count=0,
        filtered_reasons={},
        embedding_mode="enqueue",
        disable_personal_facts=False,
    )
    assert threads == 1
    assert messages == 1
    assert len(chatlog_db.created) == 1
    canonical_kwargs = chatlog_db.created[0]
    assert canonical_kwargs["origin_system"] == "anthropic"


# ---------------------------------------------------------------------------
# Explicit origin_system override (future-proofing the registry seam)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("origin_system", "import_source"),
    [
        ("openai", "openai"),
        ("anthropic", "claude"),
        ("codexify", "codexify"),
    ],
)
def test_explicit_origin_system_overrides_legacy_default(
    chatlog_db, origin_system, import_source
):
    """An explicit ``origin_system`` always wins, even when the legacy
    ``import_source`` would otherwise map to a different canonical value."""

    threads, _messages = _ingest_canonical_messages(
        chatlog_db=chatlog_db,
        user_id="account-a",
        title="Explicit override",
        thread_summary="Imported",
        import_source=import_source,
        import_profile="any",
        source_thread_id="src-override",
        messages=[_make_message("user", "hello")],
        imports_project_id=10,
        import_grouping_metadata={},
        pending_embed_items=[],
        pending_embed_message_ids=[],
        filtered_count=0,
        filtered_reasons={},
        embedding_mode="enqueue",
        disable_personal_facts=False,
        origin_system=origin_system,
    )
    assert threads == 1
    assert chatlog_db.created[0]["origin_system"] == origin_system


# ---------------------------------------------------------------------------
# Unknown import_source fails closed (does not silently map to codexify)
# ---------------------------------------------------------------------------


def test_unknown_import_source_fails_closed(chatlog_db):
    """A new external system that has not yet been added to the canonical
    registry must fail closed rather than be silently mapped to a canonical
    value. This preserves the lineage of future imported conversations."""

    with pytest.raises(ValueError, match="unknown import_source"):
        _ingest_canonical_messages(
            chatlog_db=chatlog_db,
            user_id="account-a",
            title="Unknown importer",
            thread_summary="Unknown",
            import_source="not-a-real-source",
            import_profile="not_a_real_profile",
            source_thread_id="src-unknown",
            messages=[_make_message("user", "hello")],
            imports_project_id=10,
            import_grouping_metadata={},
            pending_embed_items=[],
            pending_embed_message_ids=[],
            filtered_count=0,
            filtered_reasons={},
            embedding_mode="enqueue",
            disable_personal_facts=False,
        )
    assert chatlog_db.created == []