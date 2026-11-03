"""Restore-admission proof for untrusted native-origin claims.

ADR-016 reserves ``extra_meta.message_origin`` for the protected canonical
creation operation. A generic account restore is not that operation: an
authenticated owner may submit an archive of historical conversation content,
but a valid ZIP, a self-authored checksum, a valid manifest, and an
internally consistent set of source ids cannot prove that an uploaded
assertion was ever issued by Codexify's canonical creation path.

These tests use disposable PostgreSQL for both the export source and the
restore target, and they drive the *production* exporter and the *production*
restore entrypoint, so the archives under test are authentic archives with
authentic manifest digests.
"""

from __future__ import annotations

import io
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
import sqlalchemy as sa

from guardian.core.db import RESERVED_MESSAGE_ORIGIN_KEY
from guardian.core.pgdb import PgDB
from guardian.services.account_export import build_account_export_zip
from guardian.services.account_restore import (
    AccountRestoreService,
    AccountRestoreValidationError,
)

ACCOUNT = "restore-origin-account"
OTHER_ACCOUNT = "restore-origin-other-account"

#: The archive version the production restore can rehydrate end to end. The
#: default export version omits the explicit per-row ownership columns that
#: the canonical restore requires, so it is exercised separately below for
#: the refusal only.
RESTORABLE_SCHEMA_VERSION = "account-export.v4"

#: The exact shape a trusted writer emits. An archive carrying this is
#: indistinguishable, byte for byte, from a genuine Codexify assertion — and
#: must still be refused, because the archive cannot prove issuance.
LEGITIMATE_SHAPED_CLAIM = {
    "version": 1,
    "origin_system": "codexify",
    "asserted_at": "2026-11-01T22:00:00+00:00",
}

CHATGPT_IMPORTED_META = {
    "origin": "chatgpt_import",
    "canonical_filter_profile": "chatgpt_v1_canonical",
    "imported_at": "2026-10-31T12:00:00+00:00",
    "source_thread_id": "export-chat-1",
    "source_message_id": "export-message-1",
    "source_created_at": "2025-05-02T10:00:00+00:00",
    "raw_role": "user",
    "era": "legacy",
}

CLAUDE_IMPORTED_META = {
    "origin": "claude_import",
    "canonical_filter_profile": "claude_v1_canonical",
    "imported_at": "2026-10-31T12:00:00+00:00",
    "source_thread_id": "export-chat-2",
    "source_message_id": "export-message-2",
    "source_created_at": "2025-06-02T10:00:00+00:00",
    "raw_role": "assistant",
    "era": "legacy",
}


def _admin_database_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _database_url_for(base_url: str, database_name: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _create_disposable_database(admin_url: str, database_name: str) -> None:
    connection = psycopg.connect(admin_url, autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        connection.close()


def _drop_disposable_database(admin_url: str, database_name: str) -> None:
    connection = psycopg.connect(admin_url, autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s",
                (database_name,),
            )
            cursor.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    finally:
        connection.close()


def _migrate_to_head(database_url: str) -> None:
    from alembic.command import upgrade
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    config.config_file_name = None
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", database_url)
        patch.setenv("GUARDIAN_DATABASE_URL", database_url)
        upgrade(config, "head")


def _base_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.fail(
            "Disposable PostgreSQL proof requires explicit TEST_DATABASE_URL"
        )
    return url


@pytest.fixture(scope="module")
def source_url():
    """A disposable database that authentic exports are produced from."""
    base = _base_url()
    admin = _admin_database_url(base)
    name = f"restore_origin_src_{uuid.uuid4().hex[:10]}"
    url = _database_url_for(base, name)
    _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_disposable_database(admin, name)


@pytest.fixture(scope="module")
def target_url():
    """A disposable database that archives are restored into."""
    base = _base_url()
    admin = _admin_database_url(base)
    name = f"restore_origin_tgt_{uuid.uuid4().hex[:10]}"
    url = _database_url_for(base, name)
    _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_disposable_database(admin, name)


def _seed_account(database_url: str, user_id: str = ACCOUNT) -> None:
    """Create the account, one Project, one thread, and no messages."""
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (:id, :username, 'not-a-real-hash', 'guest') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": user_id, "username": user_id},
            )
            conn.execute(
                sa.text(
                    "INSERT INTO projects (id, user_id, name) "
                    "VALUES (1, :id, 'restore-origin') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": user_id},
            )
            conn.execute(
                sa.text(
                    "INSERT INTO chat_threads (id, user_id, title, project_id) "
                    "VALUES (10, :id, 'restore-origin thread', 1) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": user_id},
            )
    finally:
        engine.dispose()


def _seed_message(
    database_url: str,
    *,
    message_id: int,
    extra_meta: dict[str, Any] | None,
    user_id: str = ACCOUNT,
) -> None:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO chat_messages "
                    "(id, thread_id, user_id, role, content, extra_meta) "
                    "VALUES (:id, 10, :user_id, 'user', :content, CAST(:extra_meta AS jsonb))"
                ),
                {
                    "id": message_id,
                    "user_id": user_id,
                    "content": f"message {message_id}",
                    "extra_meta": json.dumps(extra_meta or {}),
                },
            )
    finally:
        engine.dispose()


def _clear_messages(database_url: str) -> None:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM chat_messages"))
    finally:
        engine.dispose()


def _clear_target(database_url: str) -> None:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM chat_messages"))
            conn.execute(sa.text("DELETE FROM chat_threads"))
            conn.execute(sa.text("DELETE FROM projects"))
    finally:
        engine.dispose()


def _export_archive(
    database_url: str, tmp_path, monkeypatch, *, schema_version: str | None = None
) -> bytes:
    """Produce an authentic account export archive from the live database."""
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("STORAGE_URL_PREFIX", "/media")
    db = PgDB(database_url)
    try:
        archive_path = build_account_export_zip(
            db, SimpleNamespace(id=ACCOUNT), schema_version=schema_version
        )
        try:
            return Path(archive_path).read_bytes()
        finally:
            if os.path.exists(archive_path):
                os.unlink(archive_path)
    finally:
        db._sa_engine.dispose()


def _target_rows(database_url: str) -> dict[str, list[dict[str, Any]]]:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            messages = [
                dict(row._mapping)
                for row in conn.execute(
                    sa.text(
                        "SELECT id, role, extra_meta FROM chat_messages "
                        "ORDER BY id"
                    )
                )
            ]
            threads = conn.execute(
                sa.text("SELECT count(*) FROM chat_threads")
            ).scalar()
            projects = conn.execute(
                sa.text("SELECT count(*) FROM projects")
            ).scalar()
        return {
            "messages": messages,
            "threads": int(threads),
            "projects": int(projects),
        }
    finally:
        engine.dispose()


def _restore(database_url: str, archive_bytes: bytes):
    db = PgDB(database_url)
    try:
        return AccountRestoreService(db).restore_from_zip(
            archive_bytes, user_id=ACCOUNT
        )
    finally:
        db._sa_engine.dispose()


def _legacy_archive_bytes(archive_bytes: bytes, schema_version: str) -> bytes:
    """Re-cut an exported archive into a legacy schema version.

    The legacy archive versions differ from the current one only in the set of
    payload families they carry, so the retained payload bytes and their
    authentic digests are reused unchanged. The current exporter cannot emit
    the legacy versions at all, so this is the only way to exercise the
    restore boundary against them.
    """
    from guardian.services.account_restore import PAYLOAD_ORDER_BY_SCHEMA

    payload_order = PAYLOAD_ORDER_BY_SCHEMA[schema_version]
    keep_families = [entry[0] for entry in payload_order]
    keep_paths = {entry[1] for entry in payload_order}

    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as source:
        manifest = json.loads(source.read("manifest.json"))
        members = {
            name: source.read(name)
            for name in source.namelist()
            if name != "manifest.json"
        }

    for path in [
        path
        for path in members
        if path.startswith("entities/") and path not in keep_paths
    ]:
        del members[path]

    integrity = manifest.get("integrity") or {}
    payload_files = {
        path: value
        for path, value in (integrity.get("payload_files") or {}).items()
        if path in members
    }
    blob_files = {
        path: value
        for path, value in (integrity.get("blob_files") or {}).items()
        if path in members
    }
    manifest["schema_version"] = schema_version
    manifest["included_families"] = list(keep_families)
    manifest["entity_counts"] = {
        family: count
        for family, count in (manifest.get("entity_counts") or {}).items()
        if family in keep_families
    }
    manifest["integrity"] = {
        "algorithm": integrity.get("algorithm"),
        "payload_files": payload_files,
        "blob_files": blob_files,
        "files": {**payload_files, **blob_files},
    }

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, body in members.items():
            archive.writestr(path, body)
        archive.writestr(
            "manifest.json", json.dumps(manifest, indent=2, sort_keys=True)
        )
    return out.getvalue()


# ---------------------------------------------------------------------------
# The refusal
# ---------------------------------------------------------------------------


def test_an_authentic_export_carrying_a_native_claim_is_refused(
    source_url, target_url, tmp_path, monkeypatch
):
    """A genuine Codexify export cannot restore through the generic path.

    The archive here is produced by the production exporter from a live
    database, so its manifest and digests are authentic. It is refused
    anyway, because the archive cannot prove that the assertion was issued by
    the protected creation operation.
    """
    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_message(
        source_url,
        message_id=1,
        extra_meta={"message_origin": LEGITIMATE_SHAPED_CLAIM},
    )

    archive = _export_archive(source_url, tmp_path, monkeypatch)

    with pytest.raises(AccountRestoreValidationError) as excinfo:
        _restore(target_url, archive)

    assert excinfo.value.code == "native_origin_claim_untrusted"
    assert excinfo.value.status_code == 400


@pytest.mark.parametrize(
    "claim",
    [
        pytest.param(LEGITIMATE_SHAPED_CLAIM, id="legitimate-shaped"),
        pytest.param(None, id="null-member"),
        pytest.param("not-an-object", id="malformed-member"),
        pytest.param(
            {"version": 99, "origin_system": "codexify", "asserted_at": "x"},
            id="unsupported-version",
        ),
        pytest.param(
            {"version": 1, "origin_system": "openai", "asserted_at": "x"},
            id="contradictory-origin-system",
        ),
        pytest.param({"asserted_at": "2026-11-01T22:00:00+00:00"}, id="partial"),
    ],
)
def test_every_shape_of_native_claim_fails_closed(
    source_url, target_url, tmp_path, monkeypatch, claim
):
    """Shape, plausibility, and manifest validity do not buy authority."""
    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_message(
        source_url,
        message_id=1,
        extra_meta={"message_origin": claim},
    )

    archive = _export_archive(source_url, tmp_path, monkeypatch)

    with pytest.raises(AccountRestoreValidationError) as excinfo:
        _restore(target_url, archive)

    assert excinfo.value.code == "native_origin_claim_untrusted"


def test_the_refusal_applies_to_every_supported_archive_version(
    source_url, target_url, tmp_path, monkeypatch
):
    """Every archive version that carries chat_messages is covered.

    The refusal is a property of the generic restore boundary, not of one
    archive version, so it is exercised against every version the restore
    service accepts. The legacy versions cannot be produced by the current
    exporter, so they are re-cut from an authentic export.
    """
    from guardian.services.account_restore import SUPPORTED_SCHEMA_VERSIONS

    _seed_account(source_url)
    _seed_account(target_url)

    for schema_version in sorted(SUPPORTED_SCHEMA_VERSIONS):
        _clear_messages(source_url)
        _clear_target(target_url)
        _seed_message(
            source_url,
            message_id=1,
            extra_meta={"message_origin": LEGITIMATE_SHAPED_CLAIM},
        )

        archive = _export_archive(
            source_url,
            tmp_path,
            monkeypatch,
            schema_version=(
                "account-export.v3"
                if schema_version in ("account-export.v1", "account-export.v2")
                else schema_version
            ),
        )
        if schema_version in ("account-export.v1", "account-export.v2"):
            archive = _legacy_archive_bytes(archive, schema_version)

        with pytest.raises(AccountRestoreValidationError) as excinfo:
            _restore(target_url, archive)

        assert excinfo.value.code == "native_origin_claim_untrusted", (
            f"archive version {schema_version} was not refused"
        )
        assert _target_rows(target_url)["messages"] == []


def test_a_refused_archive_writes_nothing_to_the_target(
    source_url, target_url, tmp_path, monkeypatch
):
    """The refusal happens before the restore transaction writes anything."""
    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_message(source_url, message_id=1, extra_meta={})
    _seed_message(
        source_url,
        message_id=2,
        extra_meta={"message_origin": LEGITIMATE_SHAPED_CLAIM},
    )

    archive = _export_archive(source_url, tmp_path, monkeypatch)

    with pytest.raises(AccountRestoreValidationError):
        _restore(target_url, archive)

    rows = _target_rows(target_url)

    assert rows["messages"] == []
    assert rows["threads"] == 0
    assert rows["projects"] == 0


def test_a_mixed_archive_is_refused_rather_than_partially_restored(
    source_url, target_url, tmp_path, monkeypatch
):
    """Valid legacy rows are not restored before the claim is found."""
    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_message(source_url, message_id=1, extra_meta={})
    _seed_message(source_url, message_id=2, extra_meta=CHATGPT_IMPORTED_META)
    _seed_message(
        source_url,
        message_id=3,
        extra_meta={"message_origin": LEGITIMATE_SHAPED_CLAIM},
    )

    archive = _export_archive(source_url, tmp_path, monkeypatch)

    with pytest.raises(AccountRestoreValidationError):
        _restore(target_url, archive)

    rows = _target_rows(target_url)

    assert rows["messages"] == []
    assert rows["threads"] == 0
    assert rows["projects"] == 0


def test_a_claim_on_an_already_existing_target_message_is_refused(
    source_url, target_url, tmp_path, monkeypatch
):
    """The refusal does not depend on the target row being absent."""
    _seed_account(source_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_account(target_url)
    _seed_message(source_url, message_id=1, extra_meta={})
    _seed_message(
        source_url,
        message_id=2,
        extra_meta={"message_origin": LEGITIMATE_SHAPED_CLAIM},
    )
    # The target already holds a message with the same canonical id.
    _seed_message(target_url, message_id=2, extra_meta={})

    archive = _export_archive(source_url, tmp_path, monkeypatch)

    with pytest.raises(AccountRestoreValidationError) as excinfo:
        _restore(target_url, archive)

    assert excinfo.value.code == "native_origin_claim_untrusted"
    rows = _target_rows(target_url)

    # The pre-existing canonical row is untouched.
    assert len(rows["messages"]) == 1
    assert rows["messages"][0]["id"] == 2
    assert RESERVED_MESSAGE_ORIGIN_KEY not in rows["messages"][0]["extra_meta"]


def test_a_claim_does_not_bypass_the_account_ownership_check(
    source_url, target_url, tmp_path, monkeypatch
):
    """A foreign-account archive is still refused by the ownership check."""
    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_account(source_url, user_id=OTHER_ACCOUNT)
    _seed_message(
        source_url,
        message_id=1,
        extra_meta={"message_origin": LEGITIMATE_SHAPED_CLAIM},
        user_id=OTHER_ACCOUNT,
    )

    archive = _export_archive(source_url, tmp_path, monkeypatch)

    with pytest.raises(AccountRestoreValidationError) as excinfo:
        _restore(target_url, archive)

    assert excinfo.value.code in {
        "native_origin_claim_untrusted",
        "user_mismatch",
    }
    rows = _target_rows(target_url)

    assert rows["messages"] == []


# ---------------------------------------------------------------------------
# Legacy and imported restores keep working
# ---------------------------------------------------------------------------


def test_unmarked_legacy_and_imported_messages_still_restore(
    source_url, target_url, tmp_path, monkeypatch
):
    """Existing unmarked and imported restore semantics are preserved."""
    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_message(source_url, message_id=1, extra_meta={})
    _seed_message(source_url, message_id=2, extra_meta=CHATGPT_IMPORTED_META)
    _seed_message(source_url, message_id=3, extra_meta=CLAUDE_IMPORTED_META)

    archive = _export_archive(
        source_url,
        tmp_path,
        monkeypatch,
        schema_version=RESTORABLE_SCHEMA_VERSION,
    )
    report = _restore(target_url, archive)

    assert report["ok"] is True
    rows = _target_rows(target_url)
    stored = {row["id"]: row["extra_meta"] for row in rows["messages"]}

    assert set(stored) == {1, 2, 3}
    # The unmarked legacy message stays unmarked; restore never mints a claim.
    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored[1]
    # The imported lineage is preserved verbatim.
    assert stored[2]["origin"] == "chatgpt_import"
    assert stored[2]["canonical_filter_profile"] == "chatgpt_v1_canonical"
    assert stored[2]["source_message_id"] == "export-message-1"
    assert stored[2]["imported_at"] == "2026-10-31T12:00:00+00:00"
    assert stored[3]["origin"] == "claude_import"
    assert stored[3]["canonical_filter_profile"] == "claude_v1_canonical"
    assert stored[3]["source_message_id"] == "export-message-2"
    # No restored row is promoted to native.
    for meta in stored.values():
        assert RESERVED_MESSAGE_ORIGIN_KEY not in meta


def test_a_restored_message_is_not_reclassified_as_native(
    source_url, target_url, tmp_path, monkeypatch
):
    """Restore preserves bytes; it does not create origin evidence."""
    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_message(source_url, message_id=1, extra_meta={})

    archive = _export_archive(
        source_url,
        tmp_path,
        monkeypatch,
        schema_version=RESTORABLE_SCHEMA_VERSION,
    )
    _restore(target_url, archive)

    rows = _target_rows(target_url)

    assert len(rows["messages"]) == 1
    assert RESERVED_MESSAGE_ORIGIN_KEY not in rows["messages"][0]["extra_meta"]


def test_the_imported_fixture_scenarios_are_not_relabelled_native(
    source_url, target_url, tmp_path, monkeypatch
):
    """ADR-016's imported assistant fixture stays imported after a restore."""
    fixtures = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "architecture"
            / "fixtures"
            / "history-message-provenance.v1.json"
        ).read_text(encoding="utf-8")
    )["fixtures"]
    imported_assistant = next(
        entry
        for entry in fixtures
        if entry["id"] == "P04"
    )["persisted_evidence"]["message"]["extra_meta"]

    _seed_account(source_url)
    _seed_account(target_url)
    _clear_messages(source_url)
    _clear_target(target_url)
    _seed_message(source_url, message_id=1, extra_meta=dict(imported_assistant))

    archive = _export_archive(
        source_url,
        tmp_path,
        monkeypatch,
        schema_version=RESTORABLE_SCHEMA_VERSION,
    )
    _restore(target_url, archive)

    rows = _target_rows(target_url)
    stored = rows["messages"][0]["extra_meta"]

    assert RESERVED_MESSAGE_ORIGIN_KEY not in stored
    assert stored["origin"] == imported_assistant["origin"]
    assert (
        stored["canonical_filter_profile"]
        == imported_assistant["canonical_filter_profile"]
    )


# ---------------------------------------------------------------------------
# The recall surface stays closed
# ---------------------------------------------------------------------------


def test_ordinary_history_tool_is_not_advertised():
    """Restoring history never makes the history tool visible."""
    from fastapi import FastAPI

    from guardian.command_bus.manifest import build_manifest
    from guardian.routes import chat, health
    from guardian.tools.chat_exposure import (
        HISTORY_SEARCH_COMMAND_ID,
        history_search_is_advertised,
        resolve_ordinary_chat_tools,
    )

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(chat.api_chat_router)
    commands = build_manifest(app).commands

    assert any(
        command.command_id == HISTORY_SEARCH_COMMAND_ID for command in commands
    )

    tools = resolve_ordinary_chat_tools(
        provider="deepseek",
        model="deepseek-model",
        provider_vendor=None,
        manifest_commands=commands,
        history_recall_grant=None,
    )

    assert tools is not None
    assert not history_search_is_advertised(tools)
