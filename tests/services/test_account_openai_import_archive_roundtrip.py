"""Disposable PostgreSQL proof of account export/restore for logical OpenAI sources."""

import hashlib
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.rag.chatgpt_migration import ingest_chatgpt_conversation_records
from guardian.core import dependencies
from guardian.core.pgdb import PgDB
from guardian.services.account_export import build_account_export_zip
from guardian.services.account_restore import (
    AccountRestoreService,
    AccountRestoreValidationError,
)
from test_account_export_v3_project_owner_roundtrip import (
    _reset,
    _seed_account,
    source_url,  # noqa: F401 -- pytest fixture
    target_url,  # noqa: F401 -- pytest fixture
)

SOURCE_A = "2f524a4b-990b-4f3a-b68d-98c78264b53d"
SOURCE_B = "b50be54a-209e-4a73-8d9d-0cb4561d74ca"
GROUP = "g-p-" + "a" * 32
DELETED_GROUP = "g-p-" + "b" * 32
OWNER = "openai-v9-owner"


def _wrong_mapping_owner(archive: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(archive)) as original:
        files = {name: original.read(name) for name in original.namelist()}
    manifest = json.loads(files["manifest.json"])
    path = "entities/openai_import_project_groups.json"
    rows = json.loads(files[path])
    rows[0]["user_id"] = "other-owner"
    body = files[path] = json.dumps(rows).encode()
    manifest["integrity"]["files"][path] = {
        "size_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
    }
    files["manifest.json"] = json.dumps(manifest).encode()
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as changed:
        for name, data in files.items():
            changed.writestr(name, data)
    return result.getvalue()


def test_openai_sources_and_project_bindings_round_trip(
    source_url, target_url, monkeypatch,  # noqa: F811 -- imported fixtures
):
    for url in (source_url, target_url):
        _reset(url)
        _seed_account(url, OWNER)

    source = PgDB(source_url)
    target = PgDB(target_url)
    with source._connect() as conn:
        conn.execute(
            """INSERT INTO projects (id, user_id, name, system_role, archived_at)
               VALUES (601, %s, 'Renamed inbox', 'general', NULL),
                      (602, %s, 'Renamed Project', NULL, NULL),
                      (603, %s, 'Archived Project', NULL, now())""",
            (OWNER, OWNER, OWNER),
        )
        conn.execute(
            """INSERT INTO openai_import_sources (id, user_id, label)
               VALUES (%s, %s, 'Renamed Pro'), (%s, %s, 'Business')""",
            (SOURCE_A, OWNER, SOURCE_B, OWNER),
        )
        conn.execute(
            """INSERT INTO openai_import_project_groups (user_id, source_id, group_id, project_id)
               VALUES (%s, %s, %s, 602), (%s, %s, %s, 603), (%s, %s, %s, NULL)""",
            (OWNER, SOURCE_A, GROUP, OWNER, SOURCE_B, GROUP, OWNER, SOURCE_B, DELETED_GROUP),
        )
        conn.execute(
            """INSERT INTO chat_threads
                   (id, user_id, title, project_id, origin_system, openai_import_source_id)
               VALUES (701, %s, 'Moved into General', 601, 'openai', %s)""",
            (OWNER, SOURCE_A),
        )

    user = SimpleNamespace(id=OWNER, username=OWNER)
    for version in ("account-export.v3", "account-export.v8"):
        with pytest.raises(RuntimeError, match="require_account_export_v9"):
            build_account_export_zip(source, user, schema_version=version)

    path = Path(build_account_export_zip(source, user))
    try:
        archive = path.read_bytes()
        restore = AccountRestoreService(target)
        parsed = restore._parse_and_validate_archive(archive, user_id=OWNER)
        assert parsed.schema_version == "account-export.v9"
        with pytest.raises(AccountRestoreValidationError) as refused:
            restore.restore_from_zip(_wrong_mapping_owner(archive), user_id=OWNER)
        assert refused.value.code == "openai_import_source_invalid"
        with target._connect() as conn:
            assert conn.execute("SELECT id FROM projects").fetchall() == []
        restore.restore_from_zip(archive, user_id=OWNER)
        restore.restore_from_zip(archive, user_id=OWNER)
    finally:
        path.unlink()

    with target._connect() as conn:
        assert {
            (r["source_id"], r["group_id"], r["project_id"])
            for r in conn.execute("SELECT * FROM openai_import_project_groups")
        } == {(SOURCE_A, GROUP, 602), (SOURCE_B, GROUP, 603), (SOURCE_B, DELETED_GROUP, None)}
        assert conn.execute(
            "SELECT project_id, openai_import_source_id FROM chat_threads WHERE id = 701"
        ).fetchone() == {"project_id": 601, "openai_import_source_id": SOURCE_A}
        assert conn.execute(
            "SELECT label FROM openai_import_sources WHERE id = %s", (SOURCE_A,)
        ).fetchone()["label"] == "Renamed Pro"
        assert conn.execute(
            "SELECT system_role FROM projects WHERE id = 601"
        ).fetchone()["system_role"] == "general"
        assert conn.execute(
            "SELECT archived_at FROM projects WHERE id = 603"
        ).fetchone()["archived_at"] is not None


    monkeypatch.setattr(dependencies, "chatlog_db", target)
    record = {
        "id": "v9-new-arrival",
        "title": "New thread for the restored exact Group ID",
        "conversation_template_id": GROUP,
        "current_node": "v9-first-message",
        "mapping": {
            "v9-first-message": {
                "id": "v9-first-message",
                "parent": None,
                "children": [],
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["A synthetic archival round trip."]},
                    "create_time": 1730419200,
                },
            },
        },
    }

    def ingest():
        return ingest_chatgpt_conversation_records(
            [record], user_id=OWNER, openai_import_source_id=SOURCE_A,
            embedding_mode="off", disable_personal_facts=True,
        )

    assert ingest()["threads_imported"] == 1
    with target._connect() as conn:
        arrival = conn.execute(
            "SELECT id, project_id FROM chat_threads WHERE metadata->>'source_thread_id' = %s",
            (record["id"],),
        ).fetchone()
        assert arrival["project_id"] == 602
        conn.execute(
            "UPDATE chat_threads SET project_id = 601 WHERE id = %s", (arrival["id"],),
        )
    assert ingest()["threads_imported"] == 0
    with target._connect() as conn:
        assert conn.execute(
            "SELECT project_id FROM chat_threads WHERE metadata->>'source_thread_id' = %s",
            (record["id"],),
        ).fetchall() == [{"project_id": 601}]
        assert conn.execute("SELECT count(*) AS n FROM projects").fetchone()["n"] == 3
