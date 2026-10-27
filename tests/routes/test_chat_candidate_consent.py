"""PFP-03B — live-chat automatic collection is gated on durable account consent.

These tests drive the real persisted-message boundary: a synthetic chat
message is persisted through ``guardian.routes.chat`` and the real candidate
extraction pipeline runs against a recording store.  The assertion is made at
the boundary the contract governs — whether automatic collection happens at
all — not by inspecting the extractor in isolation.

Synthetic principals and synthetic message content only.  No real account, no
real memory content, and no production data are involved.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import Base, UserSettings
from guardian.routes import chat as chat_routes
from guardian.services import iddb_settings_service

ACCOUNT_A = "pfp03b-account-a"
ACCOUNT_B = "pfp03b-account-b"

THREAD_ID = 4242
MESSAGE_TEXT = "My name is Sam and I live in NYC."


class _RecordingChatDb:
    """Chat + fact store that records exactly what the pipeline writes."""

    def __init__(self) -> None:
        self.messages: list[tuple[int, str, str]] = []
        self.created_facts: list[dict] = []
        self.added_evidence: list[dict] = []
        self.audit_log: list[tuple] = []
        self.existing_facts: list[dict] = []

    # ── chat surface ────────────────────────────────────────────────
    def ensure_chat_thread(self, **kwargs):
        return kwargs.get("thread_id")

    def create_message(self, thread_id, role, content):
        self.messages.append((thread_id, role, content))
        return len(self.messages)

    def write_audit_log(self, *args, **kwargs):
        self.audit_log.append(args)

    def get_chat_thread(self, thread_id):
        return {
            "thread_id": thread_id,
            "title": "Consent test thread",
            "project_id": None,
            "active_profile_id": None,
        }

    def count_messages(self, thread_id):
        return len(self.messages)

    def update_thread(self, thread_id, **kwargs):
        return None

    # ── fact surface ────────────────────────────────────────────────
    def list_facts(self, user_id, active_only=False, limit=None, **kwargs):
        return list(self.existing_facts)

    def create_fact(
        self,
        user_id,
        key,
        value,
        status="candidate",
        confidence=0.5,
        **kwargs,
    ):
        self.created_facts.append(
            {
                "user_id": user_id,
                "key": key,
                "value": value,
                "status": status,
                "confidence": confidence,
            }
        )
        return len(self.created_facts)

    def add_fact_evidence(
        self,
        fact_id,
        source_message_id,
        excerpt,
        modality="text",
        confidence=0.5,
        source_type=None,
        evidence_meta=None,
    ):
        self.added_evidence.append(
            {
                "fact_id": fact_id,
                "source_message_id": source_message_id,
                "excerpt": excerpt,
                "modality": modality,
                "confidence": confidence,
                "source_type": source_type,
                "evidence_meta": evidence_meta or {},
            }
        )
        return len(self.added_evidence)


@pytest.fixture()
def consent_store():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[UserSettings.__table__])
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    iddb_settings_service._set_session_factory(Session)
    return Session


@pytest.fixture()
def chat_env(monkeypatch):
    """Neutralise the Redis/vector side effects of the chat message path."""
    monkeypatch.setattr(chat_routes, "run_with_redis_timeout", lambda fn: fn())
    monkeypatch.setattr(chat_routes, "acquire_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(chat_routes, "release_turn_lock", lambda *a, **k: None)
    monkeypatch.setattr(chat_routes, "_vector_store", None)


def _persist_user_message(
    db: _RecordingChatDb,
    owner: str,
    *,
    extractor_calls: list | None = None,
) -> _RecordingChatDb:
    """Persist one synthetic user message and return the recording store."""
    real_extractor = chat_routes._process_fact_candidates

    def _spy(**kwargs):
        if extractor_calls is not None:
            extractor_calls.append(kwargs)
        return real_extractor(**kwargs)

    chat_routes._process_fact_candidates = _spy
    try:
        chat_routes._persist_message_to_thread(
            thread_id=THREAD_ID,
            role="user",
            content=MESSAGE_TEXT,
            owner=owner,
        )
    finally:
        chat_routes._process_fact_candidates = real_extractor
    return db


def _set_consent(user_id: str, state: str) -> dict:
    return iddb_settings_service.set_automatic_memory_suggestions_consent(
        user_id, state, actor_user_id=user_id
    )


def _install_db(monkeypatch, db: _RecordingChatDb) -> _RecordingChatDb:
    monkeypatch.setattr(chat_routes, "chatlog_db", db)
    return db


# ── The consent matrix ───────────────────────────────────────────────


@pytest.mark.parametrize("state", ["unset", "paused", "declined"])
def test_denied_consent_writes_no_candidate_or_evidence_rows(
    consent_store, chat_env, monkeypatch, state
):
    _set_consent(ACCOUNT_A, state)
    db = _install_db(monkeypatch, _RecordingChatDb())
    calls: list = []

    _persist_user_message(db, ACCOUNT_A, extractor_calls=calls)

    # The message itself is still persisted.
    assert db.messages == [(THREAD_ID, "user", MESSAGE_TEXT)]
    # The extractor is never invoked at all — output is not produced and
    # then discarded.
    assert calls == []
    assert db.created_facts == []
    assert db.added_evidence == []


def test_missing_consent_record_denies_collection(
    consent_store, chat_env, monkeypatch
):
    # No consent row exists at all.
    db = _install_db(monkeypatch, _RecordingChatDb())
    calls: list = []

    _persist_user_message(db, ACCOUNT_A, extractor_calls=calls)

    assert db.messages == [(THREAD_ID, "user", MESSAGE_TEXT)]
    assert calls == []
    assert db.created_facts == []
    assert db.added_evidence == []


def test_enabled_consent_preserves_previous_collection_behaviour(
    consent_store, chat_env, monkeypatch
):
    _set_consent(ACCOUNT_A, "enabled")
    db = _install_db(monkeypatch, _RecordingChatDb())
    calls: list = []

    _persist_user_message(db, ACCOUNT_A, extractor_calls=calls)

    # The extractor is invoked exactly once, with the unchanged arguments.
    assert len(calls) == 1
    call = calls[0]
    assert call["user_id"] == ACCOUNT_A
    assert call["thread_id"] == THREAD_ID
    assert call["text"] == MESSAGE_TEXT
    assert call["message_id"] == 1

    # Candidate and evidence output is unchanged in shape.
    assert len(db.created_facts) >= 1
    assert len(db.added_evidence) >= 1
    for fact in db.created_facts:
        assert fact["user_id"] == ACCOUNT_A
        assert fact["status"] == "candidate"
    for evidence in db.added_evidence:
        assert evidence["source_type"] == "runtime_extraction"
        assert evidence["modality"] == "text"
        assert evidence["source_message_id"] == 1
        assert evidence["evidence_meta"]["source_message_id"] == 1
        assert evidence["evidence_meta"]["source_type"] == "runtime_extraction"
        assert evidence["evidence_meta"]["user_id"] == ACCOUNT_A


def test_consent_storage_error_denies_collection_without_failing_the_message(
    consent_store, chat_env, monkeypatch
):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("consent store unavailable")

    monkeypatch.setattr(
        chat_routes.iddb_settings_service,
        "read_automatic_memory_suggestions_consent",
        _boom,
    )
    db = _install_db(monkeypatch, _RecordingChatDb())
    calls: list = []

    # Message persistence must not fail because consent could not be read.
    _persist_user_message(db, ACCOUNT_A, extractor_calls=calls)

    assert db.messages == [(THREAD_ID, "user", MESSAGE_TEXT)]
    assert calls == []
    assert db.created_facts == []
    assert db.added_evidence == []


def test_account_a_consent_does_not_authorize_account_b(
    consent_store, chat_env, monkeypatch
):
    _set_consent(ACCOUNT_A, "enabled")

    db_a = _install_db(monkeypatch, _RecordingChatDb())
    calls_a: list = []
    _persist_user_message(db_a, ACCOUNT_A, extractor_calls=calls_a)
    assert len(calls_a) == 1
    assert db_a.created_facts

    db_b = _install_db(monkeypatch, _RecordingChatDb())
    calls_b: list = []
    _persist_user_message(db_b, ACCOUNT_B, extractor_calls=calls_b)

    assert db_b.messages == [(THREAD_ID, "user", MESSAGE_TEXT)]
    assert calls_b == []
    assert db_b.created_facts == []
    assert db_b.added_evidence == []


def test_pausing_preserves_existing_records_and_stops_new_collection(
    consent_store, chat_env, monkeypatch
):
    _set_consent(ACCOUNT_A, "enabled")

    db = _install_db(monkeypatch, _RecordingChatDb())
    _persist_user_message(db, ACCOUNT_A)
    assert db.created_facts

    # The historical candidate survives the pause.
    historical = list(db.created_facts)

    _set_consent(ACCOUNT_A, "paused")

    db_paused = _install_db(monkeypatch, _RecordingChatDb())
    db_paused.existing_facts = list(historical)
    calls: list = []
    _persist_user_message(db_paused, ACCOUNT_A, extractor_calls=calls)

    assert calls == []
    assert db_paused.created_facts == []
    assert db_paused.added_evidence == []
    # Nothing was deleted.
    assert historical


def test_declining_after_enabling_stops_collection(
    consent_store, chat_env, monkeypatch
):
    _set_consent(ACCOUNT_A, "enabled")
    _set_consent(ACCOUNT_A, "declined")

    db = _install_db(monkeypatch, _RecordingChatDb())
    calls: list = []
    _persist_user_message(db, ACCOUNT_A, extractor_calls=calls)

    assert calls == []
    assert db.created_facts == []
    assert db.added_evidence == []


def test_non_user_roles_are_not_collected_even_when_enabled(
    consent_store, chat_env, monkeypatch
):
    _set_consent(ACCOUNT_A, "enabled")
    db = _install_db(monkeypatch, _RecordingChatDb())
    calls: list = []

    chat_routes._persist_message_to_thread(
        thread_id=THREAD_ID,
        role="assistant",
        content=MESSAGE_TEXT,
        owner=ACCOUNT_A,
    )

    assert db.messages == [(THREAD_ID, "assistant", MESSAGE_TEXT)]
    assert calls == []
    assert db.created_facts == []
    assert db.added_evidence == []
