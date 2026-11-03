"""Default ``account-export.v3`` Project-ownership round trip.

The default account-export artifact is ``account-export.v3``. Its bundle
reader selected candidate Projects by reachability alone, which dropped the
canonical ``projects.user_id`` that the canonical restore requires, and could
reach a Project owned by a different account.

These tests drive the **production** export builder with no schema-version
override and the **production** restore entrypoint against disposable
PostgreSQL, so the proof exercises the bundle reader rather than a fixture.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
import sqlalchemy as sa

from guardian.core.pgdb import PgDB
from guardian.services.account_export import build_account_export_zip
from guardian.services.account_restore import (
    AccountRestoreService,
    AccountRestoreValidationError,
)

ACCOUNT = "v3owner-account"
OTHER_ACCOUNT = "v3owner-other-account"

PROJECT_ID = 41001
OTHER_PROJECT_ID = 41002
THREAD_ID = 42001
MESSAGE_ID = 43001
IMPORTED_MESSAGE_ID = 43002

#: The canonical imported provenance shape, which must survive the round trip.
IMPORTED_META = {
    "origin": "chatgpt_import",
    "canonical_filter_profile": "chatgpt_v1_canonical",
    "imported_at": "2026-10-31T12:00:00+00:00",
    "source_thread_id": "export-chat-1",
    "source_message_id": "export-message-1",
    "source_created_at": "2025-05-02T10:00:00+00:00",
    "raw_role": "user",
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
    """The account whose data is exported."""
    base = _base_url()
    admin = _admin_database_url(base)
    name = f"v3owner_src_{uuid.uuid4().hex[:10]}"
    url = _database_url_for(base, name)
    _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_disposable_database(admin, name)


@pytest.fixture(scope="module")
def target_url():
    """The isolated canonical target the archive is restored into."""
    base = _base_url()
    admin = _admin_database_url(base)
    name = f"v3owner_tgt_{uuid.uuid4().hex[:10]}"
    url = _database_url_for(base, name)
    _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_disposable_database(admin, name)


def _reset(database_url: str) -> None:
    """Clear canonical rows so each case starts from the same state."""
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "TRUNCATE chat_messages, chat_threads, projects, users "
                    "CASCADE"
                )
            )
    finally:
        engine.dispose()


def _seed_account(database_url: str, account: str) -> None:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (:id, :u, 'not-a-real-hash', 'guest')"
                ),
                {"id": account, "u": account},
            )
    finally:
        engine.dispose()


def _seed_project(
    database_url: str,
    *,
    project_id: int,
    owner: str,
    name: str,
) -> None:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO projects (id, user_id, name) "
                    "VALUES (:id, :owner, :name)"
                ),
                {"id": project_id, "owner": owner, "name": name},
            )
    finally:
        engine.dispose()


def _seed_thread(
    database_url: str,
    *,
    thread_id: int,
    owner: str,
    project_id: int,
    title: str,
) -> None:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO chat_threads "
                    "(id, user_id, title, project_id) "
                    "VALUES (:id, :owner, :title, :project_id)"
                ),
                {
                    "id": thread_id,
                    "owner": owner,
                    "title": title,
                    "project_id": project_id,
                },
            )
    finally:
        engine.dispose()


def _seed_message(
    database_url: str,
    *,
    message_id: int,
    thread_id: int,
    owner: str,
    content: str,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO chat_messages "
                    "(id, thread_id, user_id, role, content, extra_meta) "
                    "VALUES (:id, :thread_id, :owner, 'user', :content, "
                    "CAST(:extra_meta AS jsonb))"
                ),
                {
                    "id": message_id,
                    "thread_id": thread_id,
                    "owner": owner,
                    "content": content,
                    "extra_meta": json.dumps(extra_meta or {}),
                },
            )
    finally:
        engine.dispose()


def _export_default_archive(database_url: str, tmp_path, monkeypatch) -> bytes:
    """Export through the production builder with no version override."""
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("STORAGE_URL_PREFIX", "/media")
    store = PgDB(database_url)
    try:
        archive_path = build_account_export_zip(store, SimpleNamespace(id=ACCOUNT))
        try:
            return Path(archive_path).read_bytes()
        finally:
            if os.path.exists(archive_path):
                os.unlink(archive_path)
    finally:
        store._sa_engine.dispose()


def _manifest_of(archive_bytes: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        return json.loads(archive.read("manifest.json"))


def _payload_of(archive_bytes: bytes, path: str) -> Any:
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        return json.loads(archive.read(path))


def _restore(database_url: str, archive_bytes: bytes):
    store = PgDB(database_url)
    try:
        return AccountRestoreService(store).restore_from_zip(
            archive_bytes, user_id=ACCOUNT
        )
    finally:
        store._sa_engine.dispose()


def _owner_of(database_url: str, table: str, pk_column: str, pk_value: int):
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            row = conn.execute(
                sa.text(
                    f"SELECT user_id FROM {table} WHERE {pk_column} = :value"
                ),
                {"value": pk_value},
            ).fetchone()
        return row[0] if row is not None else None
    finally:
        engine.dispose()


def _row_count(database_url: str, table: str) -> int:
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as conn:
            return int(conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar())
    finally:
        engine.dispose()


def _rewrite_manifest(
    archive_bytes: bytes, *, mutate_payload
) -> bytes:
    """Rebuild an archive with a mutated payload and a consistent manifest.

    ``manifest.json`` is not self-digested, so the payload digest is the only
    value that has to be recomputed.
    """
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as source:
        manifest = json.loads(source.read("manifest.json"))
        members = {
            name: source.read(name)
            for name in source.namelist()
            if name != "manifest.json"
        }

    members = mutate_payload(members, manifest)

    integrity = manifest.get("integrity") or {}
    payload_files = {}
    for path, body in members.items():
        if path.startswith("entities/"):
            payload_files[path] = {
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            }
    blob_files = {
        path: value
        for path, value in (integrity.get("blob_files") or {}).items()
        if path in members
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
# The default export carries canonical Project ownership
# ---------------------------------------------------------------------------


def test_the_default_export_identifies_itself_as_v3(source_url, tmp_path, monkeypatch):
    """The production default path emits the default archive version."""
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)

    assert _manifest_of(archive)["schema_version"] == "account-export.v3"


def test_the_default_export_carries_the_canonical_project_owner(
    source_url, tmp_path, monkeypatch
):
    """The exported Project payload carries projects.user_id."""
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)
    projects = _payload_of(archive, "entities/projects.json")

    assert len(projects) == 1
    assert projects[0]["id"] == PROJECT_ID
    assert projects[0]["user_id"] == ACCOUNT


def test_the_default_export_carries_multiple_owned_projects(
    source_url, tmp_path, monkeypatch
):
    """Every owned Project is exported with its canonical owner."""
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    for project_id, thread_id in ((PROJECT_ID, THREAD_ID), (41003, 42003)):
        _seed_project(
            source_url,
            project_id=project_id,
            owner=ACCOUNT,
            name=f"v3 project {project_id}",
        )
        _seed_thread(
            source_url,
            thread_id=thread_id,
            owner=ACCOUNT,
            project_id=project_id,
            title=f"v3 thread {thread_id}",
        )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)
    projects = _payload_of(archive, "entities/projects.json")

    assert {row["id"] for row in projects} == {PROJECT_ID, 41003}
    assert all(row["user_id"] == ACCOUNT for row in projects)


def test_the_bundle_reader_is_the_path_under_test(source_url):
    """The bundle reader itself carries the canonical owner."""
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )

    store = PgDB(source_url)
    try:
        bundle = store.fetch_account_export_bundle_for_user(ACCOUNT)
    finally:
        store._sa_engine.dispose()

    projects = bundle.get("projects") or []
    assert len(projects) == 1
    assert projects[0]["user_id"] == ACCOUNT


def test_a_foreign_owned_candidate_project_is_rejected(
    source_url, tmp_path, monkeypatch
):
    """A reachable Project owned by another account fails the export."""
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    _seed_account(source_url, OTHER_ACCOUNT)
    _seed_project(
        source_url,
        project_id=OTHER_PROJECT_ID,
        owner=OTHER_ACCOUNT,
        name="foreign project",
    )
    # An owned thread that reaches a Project owned by another account.
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=OTHER_PROJECT_ID,
        title="cross-account thread",
    )

    store = PgDB(source_url)
    try:
        with pytest.raises(RuntimeError) as excinfo:
            store.fetch_account_export_bundle_for_user(ACCOUNT)
    finally:
        store._sa_engine.dispose()

    assert "ownership" in str(excinfo.value) or "scope" in str(excinfo.value)

    with pytest.raises(RuntimeError):
        _export_default_archive(source_url, tmp_path, monkeypatch)


def test_a_missing_canonical_owner_is_rejected(source_url, tmp_path, monkeypatch):
    """A Project row without a usable canonical owner fails the export.

    A missing owner is not a defaultable value. The export refuses rather
    than defaulting the Project to the exporting account.
    """
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    # A blank account id satisfies the schema's not-null owner column while
    # carrying no usable ownership evidence.
    engine = sa.create_engine(source_url, future=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (' ', ' ', 'not-a-real-hash', 'guest')"
                )
            )
            conn.execute(
                sa.text(
                    "INSERT INTO projects (id, user_id, name) "
                    "VALUES (41004, ' ', 'blank owner project')"
                )
            )
            conn.execute(
                sa.text(
                    "INSERT INTO chat_threads (id, user_id, title, project_id) "
                    "VALUES (42004, :a, 'blank owner thread', 41004)"
                ),
                {"a": ACCOUNT},
            )
    finally:
        engine.dispose()

    store = PgDB(source_url)
    try:
        with pytest.raises(RuntimeError) as excinfo:
            store.fetch_account_export_bundle_for_user(ACCOUNT)
    finally:
        store._sa_engine.dispose()

    assert "ownership" in str(excinfo.value) or "scope" in str(excinfo.value)

    with pytest.raises(RuntimeError):
        _export_default_archive(source_url, tmp_path, monkeypatch)


def test_the_export_does_not_cross_accounts(source_url, tmp_path, monkeypatch):
    """Another account's Project, thread, and messages stay out of the archive."""
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    _seed_account(source_url, OTHER_ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )
    _seed_message(
        source_url,
        message_id=MESSAGE_ID,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        content="mine",
    )
    _seed_project(
        source_url,
        project_id=OTHER_PROJECT_ID,
        owner=OTHER_ACCOUNT,
        name="other project",
    )
    _seed_thread(
        source_url,
        thread_id=42009,
        owner=OTHER_ACCOUNT,
        project_id=OTHER_PROJECT_ID,
        title="other thread",
    )
    _seed_message(
        source_url,
        message_id=43009,
        thread_id=42009,
        owner=OTHER_ACCOUNT,
        content="theirs",
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)

    projects = _payload_of(archive, "entities/projects.json")
    threads = _payload_of(archive, "entities/chat_threads.json")
    messages = _payload_of(archive, "entities/chat_messages.json")

    assert [row["id"] for row in projects] == [PROJECT_ID]
    assert all(row["user_id"] == ACCOUNT for row in projects)
    assert all(row["id"] != 42009 for row in threads)
    assert all(row["id"] != 43009 for row in messages)
    assert all(row["user_id"] == ACCOUNT for row in messages)


# ---------------------------------------------------------------------------
# The archive is internally consistent
# ---------------------------------------------------------------------------


def test_the_default_archive_manifest_matches_its_payload(
    source_url, tmp_path, monkeypatch
):
    """Manifest digests describe the archive members they ship with."""
    _reset(source_url)
    _seed_account(source_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)
    manifest = _manifest_of(archive)

    with zipfile.ZipFile(io.BytesIO(archive), "r") as source:
        members = {name: source.read(name) for name in source.namelist()}

    declared = (manifest.get("integrity") or {}).get("files") or {}
    for path, body in members.items():
        if path == "manifest.json":
            continue
        assert path in declared, f"{path} has no declared digest"
        assert declared[path]["sha256"] == hashlib.sha256(body).hexdigest()
        assert declared[path]["size_bytes"] == len(body)


# ---------------------------------------------------------------------------
# The round trip
# ---------------------------------------------------------------------------


def test_a_default_v3_archive_restores_its_eligible_records(
    source_url, target_url, tmp_path, monkeypatch
):
    """An unmarked legacy conversation survives export and restore."""
    _reset(source_url)
    _reset(target_url)
    _seed_account(source_url, ACCOUNT)
    _seed_account(target_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )
    _seed_message(
        source_url,
        message_id=MESSAGE_ID,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        content="remember this exactly",
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)
    report = _restore(target_url, archive)

    assert report["ok"] is True
    assert _owner_of(target_url, "projects", "id", PROJECT_ID) == ACCOUNT
    assert _owner_of(target_url, "chat_threads", "id", THREAD_ID) == ACCOUNT
    assert _owner_of(target_url, "chat_messages", "id", MESSAGE_ID) == ACCOUNT

    engine = sa.create_engine(target_url, future=True)
    try:
        with engine.begin() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT thread_id, role, content, extra_meta "
                    "FROM chat_messages WHERE id = :id"
                ),
                {"id": MESSAGE_ID},
            ).fetchone()
    finally:
        engine.dispose()

    assert row is not None
    assert row[0] == THREAD_ID
    assert row[1] == "user"
    assert row[2] == "remember this exactly"
    # Restore preserves bytes; it never mints origin evidence.
    assert "message_origin" not in (row[3] or {})


def test_a_default_v3_archive_preserves_imported_provenance(
    source_url, target_url, tmp_path, monkeypatch
):
    """A canonically imported conversation keeps its imported lineage."""
    _reset(source_url)
    _reset(target_url)
    _seed_account(source_url, ACCOUNT)
    _seed_account(target_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )
    _seed_message(
        source_url,
        message_id=IMPORTED_MESSAGE_ID,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        content="imported message",
        extra_meta=dict(IMPORTED_META),
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)
    _restore(target_url, archive)

    engine = sa.create_engine(target_url, future=True)
    try:
        with engine.begin() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT extra_meta FROM chat_messages WHERE id = :id"
                ),
                {"id": IMPORTED_MESSAGE_ID},
            ).fetchone()
    finally:
        engine.dispose()

    stored = dict(row[0] or {})
    assert stored["origin"] == "chatgpt_import"
    assert stored["canonical_filter_profile"] == "chatgpt_v1_canonical"
    assert stored["source_message_id"] == "export-message-1"
    assert stored["imported_at"] == "2026-10-31T12:00:00+00:00"
    assert "message_origin" not in stored


def test_a_repeated_restore_keeps_the_established_idempotency(
    source_url, target_url, tmp_path, monkeypatch
):
    """Restoring the same archive twice is idempotent, not a duplication."""
    _reset(source_url)
    _reset(target_url)
    _seed_account(source_url, ACCOUNT)
    _seed_account(target_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )
    _seed_message(
        source_url,
        message_id=MESSAGE_ID,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        content="remember this exactly",
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)

    first = _restore(target_url, archive)
    second = _restore(target_url, archive)

    assert first["ok"] is True
    assert second["ok"] is True
    assert _row_count(target_url, "chat_messages") == 1
    assert _row_count(target_url, "chat_threads") == 1
    assert _row_count(target_url, "projects") == 1
    assert _owner_of(target_url, "projects", "id", PROJECT_ID) == ACCOUNT


# ---------------------------------------------------------------------------
# The boundaries that must not move
# ---------------------------------------------------------------------------


def test_an_older_ownerless_archive_is_not_promoted(
    source_url, target_url, tmp_path, monkeypatch
):
    """A v3 archive without Project ownership still fails explicitly."""
    _reset(source_url)
    _reset(target_url)
    _seed_account(source_url, ACCOUNT)
    _seed_account(target_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )
    _seed_message(
        source_url,
        message_id=MESSAGE_ID,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        content="remember this exactly",
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)

    def _drop_owner(members, _manifest):
        projects = json.loads(members["entities/projects.json"])
        for row in projects:
            row.pop("user_id", None)
        members["entities/projects.json"] = json.dumps(projects).encode("utf-8")
        return members

    ownerless = _rewrite_manifest(archive, mutate_payload=_drop_owner)

    with pytest.raises(Exception) as excinfo:
        _restore(target_url, ownerless)

    message = str(excinfo.value).lower()
    assert "user_id" in message or "ownership" in message

    # Nothing may be promoted into the target.
    assert _row_count(target_url, "projects") == 0
    assert _row_count(target_url, "chat_threads") == 0
    assert _row_count(target_url, "chat_messages") == 0


def test_a_native_origin_bearing_archive_remains_rejected(
    source_url, target_url, tmp_path, monkeypatch
):
    """The trusted-custody refusal from the previous slice still holds."""
    _reset(source_url)
    _reset(target_url)
    _seed_account(source_url, ACCOUNT)
    _seed_account(target_url, ACCOUNT)
    _seed_project(
        source_url, project_id=PROJECT_ID, owner=ACCOUNT, name="v3 project"
    )
    _seed_thread(
        source_url,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        project_id=PROJECT_ID,
        title="v3 thread",
    )
    _seed_message(
        source_url,
        message_id=MESSAGE_ID,
        thread_id=THREAD_ID,
        owner=ACCOUNT,
        content="a natively stamped message",
        extra_meta={
            "message_origin": {
                "version": 1,
                "origin_system": "codexify",
                "asserted_at": "2026-11-01T22:00:00+00:00",
            }
        },
    )

    archive = _export_default_archive(source_url, tmp_path, monkeypatch)

    with pytest.raises(AccountRestoreValidationError) as excinfo:
        _restore(target_url, archive)

    assert excinfo.value.code == "native_origin_claim_untrusted"
    assert _row_count(target_url, "chat_messages") == 0
    assert _row_count(target_url, "projects") == 0


def test_no_history_search_activation():
    """Repairing Project ownership advertises nothing."""
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
