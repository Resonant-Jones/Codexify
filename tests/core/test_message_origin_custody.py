"""Reserved ``extra_meta.message_origin`` custody for canonical chat messages.

These tests drive the real canonical write and enrichment paths rather than
mocking the rule under test:

* the shared custody helpers in :mod:`guardian.core.db` are exercised
  directly for their contract, and
* the actual Postgres insert (``PgDB.create_message``) and the actual
  canonical enrichment statement (``MERGE_MESSAGE_METADATA_SQL``) are
  executed against a disposable PostgreSQL database, because the merge is a
  shallow JSONB concatenation whose overwrite behaviour is a PostgreSQL
  semantic that SQLite does not reproduce.

A disposable PostgreSQL variant is required: ``TEST_DATABASE_URL`` must point
at an authority that can create databases.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

from guardian.core.db import (
    MERGE_MESSAGE_METADATA_SQL,
    RESERVED_MESSAGE_ORIGIN_KEY,
    RESERVED_MESSAGE_ORIGIN_VERSION,
    NativeOriginAssertion,
    apply_native_origin_assertion,
    build_native_user_origin_assertion,
    contains_reserved_origin,
    find_conflicting_source_lineage,
    merge_protected_message_metadata,
    strip_reserved_origin,
)
from guardian.core.pgdb import PgDB
from tests.services.test_memory_vault_read_projection import _migrate_to_head

ACCOUNT = "custody-account-a"
ORIGIN_SYSTEM = "codexify"
ASSERTED_AT = "2026-11-01T22:00:00+00:00"

#: The canonical importer's message metadata shape. An imported record carries
#: positive provider lineage and must never be given native provenance.
IMPORTED_META = {
    "origin": "chatgpt_import",
    "canonical_filter_profile": "chatgpt_v1_canonical",
    "imported_at": "2026-10-31T12:00:00+00:00",
    "source_thread_id": "export-chat-1",
    "source_message_id": "export-message-1",
    "source_created_at": "2025-05-02T10:00:00+00:00",
    "turn_index": 0,
    "raw_role": "user",
    "raw_message": {"id": "export-message-1", "author": {"role": "user"}},
    "era": "legacy",
}

#: The ADR-016 provenance fixture file. It is documentation-only, so these
#: tests read its expectations and then prove the *runtime* behaviour they
#: describe rather than treating the fixture text as proof.
PROVENANCE_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "fixtures"
    / "history-message-provenance.v1.json"
)

# A payload shaped exactly like the accepted assertion. It is untrusted
# wherever it comes from, and must never be able to establish origin.
FORGED_ASSERTION = {
    RESERVED_MESSAGE_ORIGIN_KEY: {
        "version": 1,
        "origin_system": ORIGIN_SYSTEM,
        "asserted_at": ASSERTED_AT,
    }
}

# The same shape, produced by the trusted backend capability.
TRUSTED_ASSERTION = NativeOriginAssertion(
    origin_system=ORIGIN_SYSTEM,
    asserted_at=ASSERTED_AT,
)


def _admin_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.fail(
            "Disposable PostgreSQL proof requires explicit TEST_DATABASE_URL"
        )
    return url


@pytest.fixture(scope="module")
def database_url():
    """A disposable PostgreSQL database with the canonical schema applied."""
    admin = _admin_url()
    name = "origin_custody_" + uuid.uuid4().hex
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name
    from sqlalchemy.engine import URL

    migration_url = URL.create(
        "postgresql+psycopg",
        username=info.get("user"),
        password=info.get("password"),
        host=info.get("host"),
        port=int(info.get("port", 5432)),
        database=name,
    ).render_as_string(hide_password=False)
    try:
        _migrate_to_head(migration_url)
        yield migration_url.replace("postgresql+psycopg://", "postgresql://", 1)
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def db(database_url):
    """A canonical database with one account, project, and thread."""
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE chat_messages, chat_threads, projects, users CASCADE")
        conn.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,%s,'fixture')",
            (ACCOUNT, "user-" + ACCOUNT),
        )
        conn.execute(
            "INSERT INTO projects(id,user_id,name) VALUES (1,%s,'custody')",
            (ACCOUNT,),
        )
        conn.execute(
            "INSERT INTO chat_threads(id,user_id,project_id,title,origin_system) "
            "VALUES (10,%s,1,'custody thread','codexify')",
            (ACCOUNT,),
        )
    store = PgDB(database_url)
    try:
        yield _Db(store, database_url)
    finally:
        store._sa_engine.dispose()


class _Db:
    """The canonical store plus the plain connection URL for direct reads."""

    def __init__(self, store: PgDB, url: str) -> None:
        self._store = store
        self._url = url

    def __getattr__(self, name: str):
        return getattr(self._store, name)

    @property
    def url(self) -> str:
        return self._url


def _stored_extra_meta(db, message_id: int) -> dict:
    with psycopg.connect(db.url) as conn:
        row = conn.execute(
            "SELECT extra_meta FROM chat_messages WHERE id = %s", (message_id,)
        ).fetchone()
    return dict(row[0] or {}) if row else {}


def _merge_extra_meta(db, message_id: int, payload: dict) -> None:
    """Run the canonical enrichment statement with an untrusted payload."""
    with db._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                MERGE_MESSAGE_METADATA_SQL,
                (json.dumps(payload), 10, message_id),
            )
            assert cur.fetchone() is not None


# ---------------------------------------------------------------------------
# The shared rule's contract
# ---------------------------------------------------------------------------


def test_untrusted_payload_cannot_establish_the_reserved_member():
    stripped = strip_reserved_origin(FORGED_ASSERTION)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stripped
    assert not contains_reserved_origin(stripped)


def test_unrelated_metadata_is_untouched_by_the_reserved_rule():
    payload = {
        "attachments": [{"id": "a1"}],
        "contextSource": "memory",
        RESERVED_MESSAGE_ORIGIN_KEY: {"forged": True},
    }

    stripped = strip_reserved_origin(payload)

    assert stripped == {
        "attachments": [{"id": "a1"}],
        "contextSource": "memory",
    }


def test_identical_looking_trusted_and_untrusted_json_differ_by_custody():
    """The same JSON is accepted from trusted authority and refused elsewhere."""
    untrusted = apply_native_origin_assertion(FORGED_ASSERTION, None)
    trusted = apply_native_origin_assertion(FORGED_ASSERTION, TRUSTED_ASSERTION)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in untrusted
    assert trusted[RESERVED_MESSAGE_ORIGIN_KEY] == FORGED_ASSERTION[RESERVED_MESSAGE_ORIGIN_KEY]


def test_trusted_authority_replaces_an_untrusted_claim():
    merged = apply_native_origin_assertion(FORGED_ASSERTION, TRUSTED_ASSERTION)

    assert merged[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT


def test_merge_keeps_the_stored_reserved_member():
    stored = {"message_origin": {"real": True}, "keep": 1}
    incoming = {"message_origin": {"forged": True}, "other": 2}

    merged = merge_protected_message_metadata(stored, incoming)

    assert merged["message_origin"] == {"real": True}
    assert merged["keep"] == 1
    assert merged["other"] == 2


def test_merge_cannot_create_the_reserved_member():
    merged = merge_protected_message_metadata({"keep": 1}, FORGED_ASSERTION)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in merged


# ---------------------------------------------------------------------------
# The canonical Postgres insert path
# ---------------------------------------------------------------------------


def test_client_supplied_origin_is_not_persisted(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        extra_meta={"note": "keep", **FORGED_ASSERTION},
    )

    stored = _stored_extra_meta(db, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["note"] == "keep"


def test_identical_looking_payload_is_persisted_only_from_trusted_authority(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        extra_meta=FORGED_ASSERTION,
        native_origin=TRUSTED_ASSERTION,
    )

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT


def test_trusted_authority_is_written_even_without_other_metadata(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM


def test_ordinary_native_message_creation_remains_functional(db):
    message_id = db.create_message(
        10,
        "user",
        "ordinary message",
        user_id=ACCOUNT,
        extra_meta={"contextSource": "memory"},
    )

    stored = _stored_extra_meta(db, message_id)

    assert stored == {"contextSource": "memory"}


def test_canonical_imported_metadata_remains_intact(db):
    imported_meta = {
        "origin": "chatgpt_import",
        "canonical_filter_profile": "chatgpt_v1_canonical",
        "imported_at": "2026-10-31T12:00:00+00:00",
        "source_message_id": "export-message-1",
        "source_thread_id": "export-chat-1",
    }

    message_id = db.create_message(
        10,
        "user",
        "imported message",
        user_id=ACCOUNT,
        extra_meta=imported_meta,
    )

    stored = _stored_extra_meta(db, message_id)

    assert stored == imported_meta


def test_imported_metadata_is_not_stamped_native(db):
    imported_meta = {
        "origin": "chatgpt_import",
        "source_message_id": "export-message-1",
    }

    message_id = db.create_message(
        10,
        "user",
        "imported message",
        user_id=ACCOUNT,
        extra_meta=imported_meta,
    )

    stored = _stored_extra_meta(db, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


# ---------------------------------------------------------------------------
# The canonical enrichment path
# ---------------------------------------------------------------------------


def test_generic_update_cannot_replace_an_existing_assertion(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    _merge_extra_meta(
        db,
        message_id,
        {RESERVED_MESSAGE_ORIGIN_KEY: {"forged": True}, "other": 2},
    )

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT
    assert stored["other"] == 2


def test_generic_update_cannot_remove_an_existing_assertion(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    _merge_extra_meta(db, message_id, {RESERVED_MESSAGE_ORIGIN_KEY: None})

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT


def test_generic_update_cannot_create_an_assertion(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
    )

    _merge_extra_meta(db, message_id, FORGED_ASSERTION)

    stored = _stored_extra_meta(db, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_legitimate_unrelated_metadata_update_still_works(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        extra_meta={"first": 1},
    )

    _merge_extra_meta(db, message_id, {"second": 2})

    stored = _stored_extra_meta(db, message_id)

    assert stored == {"first": 1, "second": 2}


def test_existing_assertion_survives_enrichment(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    _merge_extra_meta(db, message_id, {"turn_id": "turn-1"})

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT
    assert stored["turn_id"] == "turn-1"


def test_unknown_legacy_record_remains_unknown(db):
    with psycopg.connect(db.url) as conn:
        conn.execute(
            "INSERT INTO chat_messages(id,thread_id,user_id,role,content,extra_meta) "
            "VALUES (777,10,%s,'user','legacy','{}'::jsonb)",
            (ACCOUNT,),
        )

    _merge_extra_meta(db, 777, {"turn_id": "turn-1"})

    stored = _stored_extra_meta(db, 777)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["turn_id"] == "turn-1"


def test_failed_update_leaves_existing_state_unchanged(db):
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )
    before = _stored_extra_meta(db, message_id)

    with db._connect() as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.Error):
                cur.execute(
                    MERGE_MESSAGE_METADATA_SQL,
                    ("not json", 10, message_id),
                )

    assert _stored_extra_meta(db, message_id) == before


def test_failed_insert_writes_no_row(db):
    with pytest.raises(Exception):
        db.create_message(
            10,
            "user",
            "hello",
            user_id=ACCOUNT,
            # A set is not JSON-serializable, so the insert fails outright.
            extra_meta={"bad": {1, 2}},
        )

    with psycopg.connect(db.url) as conn:
        count = conn.execute(
            "SELECT count(*) FROM chat_messages WHERE thread_id = 10 AND user_id = %s",
            (ACCOUNT,),
        ).fetchone()[0]

    assert count == 0


def test_imported_lineage_survives_generic_enrichment(db):
    imported_meta = {
        "origin": "chatgpt_import",
        "canonical_filter_profile": "chatgpt_v1_canonical",
        "source_message_id": "export-message-1",
    }
    message_id = db.create_message(
        10,
        "user",
        "imported message",
        user_id=ACCOUNT,
        extra_meta=imported_meta,
    )

    _merge_extra_meta(db, message_id, {"turn_id": "turn-1"})

    stored = _stored_extra_meta(db, message_id)

    assert stored["origin"] == "chatgpt_import"
    assert stored["canonical_filter_profile"] == "chatgpt_v1_canonical"
    assert stored["source_message_id"] == "export-message-1"
    assert stored["turn_id"] == "turn-1"


def test_jsonb_shape_of_the_canonical_merge_is_stable():
    """The canonical statement keeps its PostgreSQL JSONB semantics."""
    assert "- 'message_origin'" in MERGE_MESSAGE_METADATA_SQL
    assert "||" in MERGE_MESSAGE_METADATA_SQL


def test_reserved_member_is_a_plain_top_level_key():
    """Only the exact top-level member is reserved."""
    nested = {"outer": {RESERVED_MESSAGE_ORIGIN_KEY: {"forged": True}}}

    assert contains_reserved_origin(nested) is False
    assert strip_reserved_origin(nested) == nested


def test_stored_jsonb_column_is_not_a_text_column(db):
    """The reserved member lives in a JSONB column, so merges are structured."""
    with psycopg.connect(db.url) as conn:
        data_type = conn.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'chat_messages' AND column_name = 'extra_meta'"
        ).fetchone()[0]

    assert data_type == "jsonb"


def test_jsonb_payload_is_accepted_by_the_canonical_merge(db):
    """A realistic JSONB metadata shape merges without error."""
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        extra_meta={"attachments": [{"id": "a1", "kind": "image"}]},
    )

    with db._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                MERGE_MESSAGE_METADATA_SQL,
                (json.dumps({"attachments": [{"id": "a2"}]}), 10, message_id),
            )

    stored = _stored_extra_meta(db, message_id)

    assert stored["attachments"] == [{"id": "a2"}]


def test_untrusted_payload_cannot_reach_the_reserved_member_via_jsonb(db):
    """The canonical statement subtracts the reserved key from the payload."""
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
    )

    with db._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                MERGE_MESSAGE_METADATA_SQL,
                (json.dumps(FORGED_ASSERTION), 10, message_id),
            )

    stored = _stored_extra_meta(db, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_jsonb_merge_preserves_stored_member_against_a_jsonb_payload(db):
    """The stored assertion survives a JSONB payload that mimics it."""
    message_id = db.create_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        native_origin=TRUSTED_ASSERTION,
    )

    with db._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                MERGE_MESSAGE_METADATA_SQL,
                (Jsonb(FORGED_ASSERTION), 10, message_id),
            )

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] == ASSERTED_AT


# ---------------------------------------------------------------------------
# Trusted native creation at the adapter boundary
# ---------------------------------------------------------------------------


def _stored_assertion(db, message_id: int) -> dict:
    stored = _stored_extra_meta(db, message_id)
    return dict(stored.get(RESERVED_MESSAGE_ORIGIN_KEY) or {})


def test_the_trusted_native_writer_stamps_the_reserved_member(db):
    """The trusted creation seam writes positive native-origin evidence."""
    message_id = db.create_native_user_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
    )

    assertion = _stored_assertion(db, message_id)

    assert assertion["version"] == RESERVED_MESSAGE_ORIGIN_VERSION
    assert assertion["origin_system"] == ORIGIN_SYSTEM


def test_the_trusted_native_writer_generates_its_own_zoned_timestamp(db):
    """The assertion timestamp is backend-generated and timezone-aware."""
    message_id = db.create_native_user_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
    )

    asserted_at = _stored_assertion(db, message_id)["asserted_at"]
    moment = datetime.fromisoformat(asserted_at)

    assert moment.tzinfo is not None
    assert moment.utcoffset() == timedelta(0)
    assert asserted_at != ASSERTED_AT


def test_the_trusted_native_writer_replaces_a_forged_client_claim(db):
    """A client-shaped claim never controls the stored assertion."""
    message_id = db.create_native_user_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        extra_meta={**FORGED_ASSERTION, "note": "keep"},
    )

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["asserted_at"] != ASSERTED_AT
    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["version"] == (
        RESERVED_MESSAGE_ORIGIN_VERSION
    )
    assert stored[RESERVED_MESSAGE_ORIGIN_KEY]["origin_system"] == ORIGIN_SYSTEM
    assert stored["note"] == "keep"


def test_the_generic_writer_is_not_a_native_creation_authority(db):
    """The importer's helper must never stamp native provenance."""
    message_id = db.create_message(
        10,
        "user",
        "imported message",
        user_id=ACCOUNT,
        extra_meta=IMPORTED_META,
    )

    stored = _stored_extra_meta(db, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored == IMPORTED_META


def test_the_importer_keeps_using_the_generic_helper():
    """The canonical importer is not wired to the trusted native seam."""
    source = (
        Path(__file__).resolve().parents[2]
        / "backend"
        / "rag"
        / "chatgpt_migration.py"
    ).read_text(encoding="utf-8")

    assert "create_native_user_message" not in source
    assert "chatlog_db.create_message(" in source


def test_a_failed_native_insert_leaves_no_row_and_no_assertion(db):
    """A failing insert cannot leave an apparently proven orphan behind."""
    with pytest.raises(psycopg.Error):
        db.create_native_user_message(
            9999,
            "user",
            "hello",
            user_id=ACCOUNT,
        )

    with psycopg.connect(db.url) as conn:
        count = conn.execute(
            "SELECT count(*) FROM chat_messages WHERE thread_id = 9999"
        ).fetchone()[0]

    assert count == 0


def test_a_replayed_write_preserves_the_original_assertion(db):
    """Re-running the write keeps the original assertion and identity."""
    message_id = db.create_native_user_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
        extra_meta={"note": "keep"},
    )
    original = _stored_extra_meta(db, message_id)

    _merge_extra_meta(db, message_id, dict(original))
    _merge_extra_meta(db, message_id, FORGED_ASSERTION)

    stored = _stored_extra_meta(db, message_id)

    assert stored[RESERVED_MESSAGE_ORIGIN_KEY] == (
        original[RESERVED_MESSAGE_ORIGIN_KEY]
    )
    assert stored["note"] == "keep"


def test_two_native_creations_are_two_independent_assertions(db):
    """Each native creation is its own record with its own identity."""
    first = db.create_native_user_message(10, "user", "hello", user_id=ACCOUNT)
    second = db.create_native_user_message(10, "user", "hello", user_id=ACCOUNT)

    assert first != second
    assert (
        _stored_assertion(db, first)["asserted_at"]
        != _stored_assertion(db, second)["asserted_at"]
    )


def test_the_builder_refuses_a_naive_timestamp():
    """A naive timestamp is normalized rather than stored without a zone."""
    assertion = build_native_user_origin_assertion(
        asserted_at=datetime(2026, 11, 1, 22, 0, 0)
    )

    moment = datetime.fromisoformat(assertion.asserted_at)

    assert moment.utcoffset() == timedelta(0)


def test_conflicting_source_lineage_is_detected():
    """The ordinary-chat guard can see importer-origin claims."""
    assert find_conflicting_source_lineage(IMPORTED_META) == sorted(
        IMPORTED_META.keys()
    )
    assert find_conflicting_source_lineage({"note": "keep"}) == []
    assert find_conflicting_source_lineage(None) == []


# ---------------------------------------------------------------------------
# The ADR-016 provenance fixtures, proven against the runtime
# ---------------------------------------------------------------------------


def _provenance_fixture() -> dict:
    return json.loads(PROVENANCE_FIXTURE_PATH.read_text(encoding="utf-8"))


def _fixture_by_id(fixture_id: str) -> dict:
    for entry in _provenance_fixture()["fixtures"]:
        if entry["id"] == fixture_id:
            return entry
    raise AssertionError(f"provenance fixture {fixture_id!r} is missing")


@pytest.mark.parametrize("fixture_id", ["P01", "P06"])
def test_the_native_fixtures_describe_what_the_trusted_writer_produces(
    db, fixture_id
):
    """P01/P06's stored evidence is the shape the trusted writer produces."""
    fixture = _fixture_by_id(fixture_id)
    expected = fixture["persisted_evidence"]["message"]["extra_meta"]
    expected_assertion = expected[RESERVED_MESSAGE_ORIGIN_KEY]

    message_id = db.create_native_user_message(
        10,
        "user",
        "hello",
        user_id=ACCOUNT,
    )
    stored = _stored_assertion(db, message_id)

    assert set(stored) == set(expected_assertion)
    assert stored["version"] == expected_assertion["version"]
    assert stored["origin_system"] == expected_assertion["origin_system"]
    assert fixture["expected_origin_classification"] == "native"


@pytest.mark.parametrize("fixture_id", ["P05", "N01", "N05"])
def test_the_imported_and_legacy_fixtures_are_preserved_verbatim(
    db, fixture_id
):
    """Imported and legacy records keep their evidence and gain nothing."""
    fixture = _fixture_by_id(fixture_id)
    expected = fixture["persisted_evidence"]["message"]["extra_meta"]

    message_id = db.create_message(
        10,
        "user",
        "fixture row",
        user_id=ACCOUNT,
        extra_meta=expected,
    )
    stored = _stored_extra_meta(db, message_id)

    assert stored == expected
    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


def test_the_conflicting_fixture_keeps_its_lineage_and_loses_the_native_claim(db):
    """N03: the import lineage survives; the forged native claim does not."""
    fixture = _fixture_by_id("N03")
    expected = fixture["persisted_evidence"]["message"]["extra_meta"]

    message_id = db.create_message(
        10,
        "user",
        "fixture row",
        user_id=ACCOUNT,
        extra_meta=expected,
    )
    stored = _stored_extra_meta(db, message_id)

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["origin"] == expected["origin"]
    assert stored["canonical_filter_profile"] == expected[
        "canonical_filter_profile"
    ]
    assert stored["source_message_id"] == expected["source_message_id"]


def test_the_untrusted_claim_fixture_stays_unknown(db):
    """N04: a native-looking claim without writer authority proves nothing."""
    fixture = _fixture_by_id("N04")
    expected = fixture["persisted_evidence"]["message"]["extra_meta"]

    message_id = db.create_message(
        10,
        "user",
        "fixture row",
        user_id=ACCOUNT,
        extra_meta=expected,
    )
    stored = _stored_extra_meta(db, message_id)

    assert stored == {}
    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored


# ---------------------------------------------------------------------------
# Restore compatibility
# ---------------------------------------------------------------------------


def test_restore_preserves_the_original_evidence_and_adds_no_native_origin(db):
    """A restored record keeps its proof and is not re-stamped as native."""
    imported_fixture = _fixture_by_id("N05")
    native_fixture = _fixture_by_id("P01")
    native_assertion = native_fixture["persisted_evidence"]["message"][
        "extra_meta"
    ][RESERVED_MESSAGE_ORIGIN_KEY]

    db.restore_account_export_chat_messages(
        [
            {
                "id": 901,
                "thread_id": 10,
                "user_id": ACCOUNT,
                "role": "user",
                "content": "restored imported row",
                "event_at": "2026-10-31T12:00:00+00:00",
                "kind": "chat",
                "extra_meta": imported_fixture["persisted_evidence"]["message"][
                    "extra_meta"
                ],
                "created_at": "2026-10-31T12:00:00+00:00",
            },
            {
                "id": 902,
                "thread_id": 10,
                "user_id": ACCOUNT,
                "role": "user",
                "content": "restored native row",
                "event_at": "2026-11-01T22:00:00+00:00",
                "kind": "chat",
                "extra_meta": native_fixture["persisted_evidence"]["message"][
                    "extra_meta"
                ],
                "created_at": "2026-11-01T22:00:00+00:00",
            },
        ],
        target_user_id=ACCOUNT,
    )

    restored_imported = _stored_extra_meta(db, 901)
    restored_native = _stored_extra_meta(db, 902)

    assert restored_imported == imported_fixture["persisted_evidence"]["message"][
        "extra_meta"
    ]
    assert RESERVED_MESSAGE_ORIGIN_KEY not in restored_imported
    assert restored_native[RESERVED_MESSAGE_ORIGIN_KEY] == native_assertion
