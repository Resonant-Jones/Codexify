from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cognition.system_profiles import store as persona_store
from guardian.core import pgdb as pgdb_module
from guardian.db.models import (
    Base,
    PersonaProfile,
    PersonaProfileBinding,
    PersonaProfileRevision,
    User,
)
from guardian.services.account_export import (
    PAYLOAD_FAMILIES,
    build_account_export_zip,
)
from guardian.services.account_restore import (
    AccountRestoreConflictError,
    AccountRestoreService,
    AccountRestoreValidationError,
)
from tests.migration.test_persona_profile_manifest_binding_migration import (
    temporary_postgres as temporary_postgres,  # noqa: PLC0414
)

ACCOUNT_A = "account-a"
ACCOUNT_B = "account-b"


def _timestamp(day: int) -> str:
    return f"2026-09-{day:02d}T12:00:00+00:00"


def _manifest(profile_id: str, revision: int, *, name: str) -> dict[str, Any]:
    return {
        "apiVersion": "codexify.persona/v1",
        "profileIdentity": profile_id,
        "revision": revision,
        "identity": {"name": name, "description": f"revision {revision}"},
        "prompt": {
            "systemPrompt": f"Prompt {revision}",
            "styleNotes": "Precise and grounded.",
            "directives": "Never infer authority.",
        },
        "model": {
            "provider": "openai",
            "model": f"gpt-profile-{revision}",
            "temperature": revision / 10,
            "topK": 16,
            "topP": 0.9,
            "maxTokens": 2048,
        },
        "voice": {
            "enabled": True,
            "provider": "elevenlabs",
            "voicePreset": "calm",
            "speed": 1.0,
            "wakeWord": "Axis",
            "interruptible": True,
        },
        "capabilities": {
            "pinnedTools": ["web-search"],
            "allowedTools": ["web-search", "calculator"],
            "skills": ["critical-thinking"],
            "permissions": {
                "web": True,
                "email": False,
                "calendar": False,
                "cli": False,
                "filesystem": True,
            },
        },
        "retrieval": {
            "enabled": True,
            "mode": "hybrid",
            "topK": 8,
            "rerank": True,
        },
    }


class ScopedExportDB:
    def __init__(self) -> None:
        self.threads = []
        self.profiles = {
            "a-1": {"id": "a-1", "current_revision": 3},
            "a-2": {"id": "a-2", "current_revision": 1},
            "b-1": {"id": "b-1", "current_revision": 1},
            "unbound": {"id": "unbound", "current_revision": 1},
        }
        for index, row in enumerate(self.profiles.values(), start=1):
            row.update(
                created_at=_timestamp(index),
                updated_at=_timestamp(index + 1),
            )
        self.bindings = {
            "a-1": ACCOUNT_A,
            "a-2": ACCOUNT_A,
            "b-1": ACCOUNT_B,
        }
        self.revisions = []
        profile_counts = (
            ("a-1", 3),
            ("a-2", 1),
            ("b-1", 1),
            ("unbound", 1),
        )
        for profile_id, count in profile_counts:
            for revision in range(1, count + 1):
                self.revisions.append(
                    {
                        "profile_id": profile_id,
                        "revision": revision,
                        "api_version": "codexify.persona/v1",
                        "manifest_json": _manifest(
                            profile_id,
                            revision,
                            name=f"{profile_id} revision {revision}",
                        ),
                        "created_at": _timestamp(revision),
                    }
                )

    def fetch_account_export_bundle_for_user(
        self, user_id: str
    ) -> dict[str, list[dict[str, Any]]]:
        bound_ids = {
            profile_id
            for profile_id, owner in self.bindings.items()
            if owner == user_id
        }
        bundle = {family: [] for family in PAYLOAD_FAMILIES}
        bundle["chat_threads"] = deepcopy(self.threads)
        bundle["persona_profiles"] = [
            deepcopy(self.profiles[profile_id]) for profile_id in sorted(bound_ids)
        ]
        bundle["persona_profile_revisions"] = [
            deepcopy(row) for row in self.revisions if row["profile_id"] in bound_ids
        ]
        bundle["persona_profile_bindings"] = [
            {
                "profile_id": profile_id,
                "owner_account_id": user_id,
                "created_at": _timestamp(1),
                "updated_at": _timestamp(2),
            }
            for profile_id in sorted(bound_ids)
        ]
        return bundle


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=None)


class SqlAlchemyRestoreDB:
    """Small persistence adapter proving the production restore service seam."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory
        self.threads = {}

    def __getattr__(self, name: str):
        if name.startswith("restore_account_export_"):
            return lambda rows, **_kwargs: {
                "imported": len(rows),
                "skipped": 0,
                "failed": 0,
                "unresolved": 0,
            }
        raise AttributeError(name)

    def get_chat_thread(self, thread_id):
        return deepcopy(self.threads.get(thread_id))

    def restore_account_export_chat_threads(self, rows, **_kwargs):
        imported = skipped = 0
        with self.session_factory() as session:
            for row in rows:
                revision = row["active_profile_revision"]
                if revision is not None:
                    assert (
                        session.get(
                            PersonaProfileRevision, (row["active_profile_id"], revision)
                        )
                        is not None
                    )
                    assert (
                        session.get(
                            PersonaProfileBinding, row["active_profile_id"]
                        ).owner_account_id
                        == row["user_id"]
                    )
                if row["id"] in self.threads:
                    assert self.threads[row["id"]] == row
                    skipped += 1
                else:
                    self.threads[row["id"]] = deepcopy(row)
                    imported += 1
        return self._counts(imported, skipped)

    @staticmethod
    def _counts(imported: int, skipped: int) -> dict[str, int]:
        return {
            "imported": imported,
            "skipped": skipped,
            "failed": 0,
            "unresolved": 0,
        }

    def restore_account_export_persona_profiles(self, rows, **_kwargs):
        imported = skipped = 0
        with self.session_factory.begin() as session:
            for row in rows:
                existing = session.get(PersonaProfile, row["id"])
                expected = {
                    key: row[key]
                    for key in (
                        "name",
                        "system_prompt",
                        "model_provider",
                        "model_id",
                        "temperature",
                        "current_revision",
                    )
                }
                if existing is not None:
                    actual = {key: getattr(existing, key) for key in expected}
                    if actual != expected:
                        raise ValueError("persona_profile registry conflict")
                    skipped += 1
                    continue
                session.add(
                    PersonaProfile(
                        **expected,
                        id=row["id"],
                        created_at=_dt(row["created_at"]),
                        updated_at=_dt(row["updated_at"]),
                    )
                )
                imported += 1
        return self._counts(imported, skipped)

    def restore_account_export_persona_profile_revisions(self, rows, **_kwargs):
        imported = skipped = 0
        with self.session_factory.begin() as session:
            for row in rows:
                key = {
                    "profile_id": row["profile_id"],
                    "revision": row["revision"],
                }
                existing = session.get(PersonaProfileRevision, key)
                if existing is not None:
                    if (
                        existing.api_version != row["api_version"]
                        or existing.manifest_json != row["manifest_json"]
                        or existing.created_at != _dt(row["created_at"])
                    ):
                        raise ValueError("immutable Persona Profile revision conflict")
                    skipped += 1
                    continue
                session.add(
                    PersonaProfileRevision(
                        **key,
                        api_version=row["api_version"],
                        manifest_json=row["manifest_json"],
                        created_at=_dt(row["created_at"]),
                    )
                )
                imported += 1
        return self._counts(imported, skipped)

    def restore_account_export_persona_profile_bindings(
        self, rows, *, target_user_id: str, **_kwargs
    ):
        imported = skipped = 0
        with self.session_factory.begin() as session:
            for row in rows:
                existing = session.get(PersonaProfileBinding, row["profile_id"])
                if existing is not None:
                    if existing.owner_account_id != target_user_id:
                        raise ValueError("Persona Profile binding conflict")
                    skipped += 1
                    continue
                session.add(
                    PersonaProfileBinding(
                        profile_id=row["profile_id"],
                        owner_account_id=target_user_id,
                        created_at=_dt(row["created_at"]),
                        updated_at=_dt(row["updated_at"]),
                    )
                )
                imported += 1
        return self._counts(imported, skipped)


@contextmanager
def _target_store():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            PersonaProfile.__table__,
            PersonaProfileRevision.__table__,
            PersonaProfileBinding.__table__,
        ],
    )
    factory = sessionmaker(bind=engine, future=True)
    with factory.begin() as session:
        session.add_all(
            [
                User(
                    id=ACCOUNT_A,
                    username=ACCOUNT_A,
                    password_hash="x",
                    role="guest",
                ),
                User(
                    id=ACCOUNT_B,
                    username=ACCOUNT_B,
                    password_hash="x",
                    role="guest",
                ),
            ]
        )
    persona_store._set_session_factory(factory)
    try:
        yield factory
    finally:
        persona_store._set_session_factory(None)
        engine.dispose()


def _archive_bytes(export_db: ScopedExportDB, tmp_path: Path) -> bytes:
    os.environ.setdefault("STORAGE_BASE_PATH", str(tmp_path / "storage"))
    path = build_account_export_zip(export_db, SimpleNamespace(id=ACCOUNT_A))
    try:
        return Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)


def _read_archive(archive_bytes: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        payloads = {
            family: json.loads(archive.read(f"entities/{family}.json"))
            for family in PAYLOAD_FAMILIES
        }
    return manifest, payloads


def _rewrite_payload(archive_bytes: bytes, family: str, mutate) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(archive_bytes), "r")
    bodies = {name: source.read(name) for name in source.namelist()}
    source.close()
    path = f"entities/{family}.json"
    rows = json.loads(bodies[path])
    mutate(rows)
    bodies[path] = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    manifest = json.loads(bodies["manifest.json"])
    digest = manifest["integrity"]["files"][path]
    digest["sha256"] = hashlib.sha256(bodies[path]).hexdigest()
    digest["size_bytes"] = len(bodies[path])
    manifest["integrity"]["payload_files"][path] = dict(digest)
    manifest["entity_counts"][family] = len(rows)
    bodies["manifest.json"] = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for name, body in bodies.items():
            target.writestr(name, body)
    return buffer.getvalue()


def test_v3_persona_profiles_round_trip_all_revisions_and_account_scope(tmp_path):
    source = ScopedExportDB()
    archive_bytes = _archive_bytes(source, tmp_path)
    manifest, payloads = _read_archive(archive_bytes)

    assert manifest["schema_version"] == "account-export.v3"
    assert set(manifest["included_families"]) == set(PAYLOAD_FAMILIES)
    assert [row["id"] for row in payloads["persona_profiles"]] == ["a-1", "a-2"]
    assert [row["profile_id"] for row in payloads["persona_profile_bindings"]] == [
        "a-1",
        "a-2",
    ]
    assert [
        (row["profile_id"], row["revision"])
        for row in payloads["persona_profile_revisions"]
    ] == [("a-1", 1), ("a-1", 2), ("a-1", 3), ("a-2", 1)]
    assert "b-1" not in json.dumps(payloads)
    assert "unbound" not in json.dumps(payloads)

    with _target_store() as factory:
        service = AccountRestoreService(SqlAlchemyRestoreDB(factory))
        first = service.restore_from_zip(archive_bytes, user_id=ACCOUNT_A)
        second = service.restore_from_zip(archive_bytes, user_id=ACCOUNT_A)
        assert first["ok"] is True
        assert second["counts"]["imported"] == 0
        assert second["counts"]["skipped"] == 8

        restored = persona_store.list_persona_profiles(account_id=ACCOUNT_A)
        assert [profile.id for profile in restored] == ["a-1", "a-2"]
        assert restored[0].current_revision == 3
        assert restored[0].name == "a-1 revision 3"
        assert restored[0].system_prompt == "Prompt 3"
        assert restored[0].model_id == "gpt-profile-3"
        assert restored[0].manifest.model.temperature == 0.3
        assert restored[0].manifest.voice is not None
        assert restored[0].manifest.capabilities is not None
        assert restored[0].manifest.retrieval is not None
        with factory() as session:
            history = list(
                session.scalars(
                    select(PersonaProfileRevision)
                    .where(PersonaProfileRevision.profile_id == "a-1")
                    .order_by(PersonaProfileRevision.revision)
                )
            )
            assert [row.revision for row in history] == [1, 2, 3]
            assert [row.manifest_json for row in history] == [
                _manifest("a-1", revision, name=f"a-1 revision {revision}")
                for revision in (1, 2, 3)
            ]


@pytest.mark.parametrize(
    "family,mutate",
    [
        (
            "persona_profile_revisions",
            lambda rows: rows[0]["manifest_json"].update(
                {"profileIdentity": "different-profile"}
            ),
        ),
        (
            "persona_profile_revisions",
            lambda rows: rows[0]["manifest_json"].update({"revision": 99}),
        ),
        (
            "persona_profiles",
            lambda rows: rows[0].update({"current_revision": 99}),
        ),
        (
            "persona_profile_bindings",
            lambda rows: rows[0].update({"owner_account_id": ACCOUNT_B}),
        ),
    ],
)
def test_v3_persona_profile_semantic_tampering_fails_before_restore(
    tmp_path, family, mutate
):
    archive_bytes = _archive_bytes(ScopedExportDB(), tmp_path)
    tampered = _rewrite_payload(archive_bytes, family, mutate)
    with _target_store() as factory:
        with pytest.raises(AccountRestoreValidationError):
            AccountRestoreService(SqlAlchemyRestoreDB(factory)).restore_from_zip(
                tampered,
                user_id=ACCOUNT_A,
            )
        assert persona_store.list_persona_profiles(account_id=ACCOUNT_A) == []


def test_v3_persona_profile_revision_conflict_fails_closed(tmp_path):
    archive_bytes = _archive_bytes(ScopedExportDB(), tmp_path)
    with _target_store() as factory:
        service = AccountRestoreService(SqlAlchemyRestoreDB(factory))
        service.restore_from_zip(archive_bytes, user_id=ACCOUNT_A)
        with factory.begin() as session:
            revision = session.get(
                PersonaProfileRevision,
                {"profile_id": "a-1", "revision": 2},
            )
            assert revision is not None
            revision.manifest_json = {
                **revision.manifest_json,
                "prompt": {"systemPrompt": "Conflicting persisted history"},
            }
        with pytest.raises(AccountRestoreConflictError):
            service.restore_from_zip(archive_bytes, user_id=ACCOUNT_A)


def test_export_rejects_malformed_persisted_persona_manifest(tmp_path):
    source = ScopedExportDB()
    source.revisions[0]["manifest_json"]["profileIdentity"] = "wrong-profile"

    with pytest.raises(
        RuntimeError,
        match="persona_profile_export_revision_mismatch",
    ):
        _archive_bytes(source, tmp_path)


def test_production_pgdb_reader_scopes_personas_through_account_binding(
    monkeypatch: pytest.MonkeyPatch,
):
    source = ScopedExportDB()
    executed_sql: list[str] = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/test")

    class Cursor:
        def __init__(self) -> None:
            self.rows: list[dict[str, Any]] = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=()):
            statement = str(query)
            executed_sql.append(statement)
            user_id = params[0] if params else None
            bound_ids = {
                profile_id
                for profile_id, owner in source.bindings.items()
                if owner == user_id
            }
            if "FROM persona_profiles AS p" in statement:
                self.rows = [
                    deepcopy(source.profiles[profile_id])
                    for profile_id in sorted(bound_ids)
                ]
            elif "FROM persona_profile_revisions AS r" in statement:
                self.rows = [
                    deepcopy(row)
                    for row in source.revisions
                    if row["profile_id"] in bound_ids
                ]
            elif "FROM persona_profile_bindings" in statement:
                self.rows = [
                    {
                        "profile_id": profile_id,
                        "owner_account_id": user_id,
                        "created_at": _timestamp(1),
                        "updated_at": _timestamp(2),
                    }
                    for profile_id in sorted(bound_ids)
                ]
            else:
                self.rows = []

        def fetchall(self):
            return self.rows

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(
        pgdb_module.psycopg,
        "connect",
        lambda *_args, **_kwargs: Connection(),
    )
    bundle = pgdb_module.fetch_account_export_bundle_for_user(ACCOUNT_A)

    assert [row["id"] for row in bundle["persona_profiles"]] == ["a-1", "a-2"]
    assert {row["profile_id"] for row in bundle["persona_profile_revisions"]} == {
        "a-1",
        "a-2",
    }
    assert {row["profile_id"] for row in bundle["persona_profile_bindings"]} == {
        "a-1",
        "a-2",
    }
    persona_sql = "\n".join(
        statement for statement in executed_sql if "persona_profile" in statement
    )
    assert "JOIN persona_profile_bindings" in persona_sql
    assert "WHERE b.owner_account_id = %s" in persona_sql
    assert "WHERE owner_account_id = %s" in persona_sql


def _pinned_thread():
    return {
        "id": 42,
        "user_id": ACCOUNT_A,
        "title": "Pinned thread",
        "summary": "",
        "project_id": None,
        "parent_id": None,
        "archived_at": None,
        "active_profile_id": "a-1",
        "active_profile_revision": 1,
        "metadata": {},
        "is_diary": False,
        "diary_mode": False,
        "exclude_from_identity": False,
        "modeling_excluded": False,
        "created_at": _timestamp(1),
        "updated_at": _timestamp(1),
    }


@pytest.mark.parametrize("old_v3", [False, True])
def test_thread_revision_round_trip_and_old_v3_derivation(tmp_path, old_v3):
    from guardian.cognition.system_profiles.resolver import (
        resolve_thread_system_profile,
    )

    source = ScopedExportDB()
    source.threads = [_pinned_thread()]
    archive = _archive_bytes(source, tmp_path)
    _, payloads = _read_archive(archive)
    assert payloads["chat_threads"][0]["active_profile_revision"] == 1
    if old_v3:
        archive = _rewrite_payload(
            archive, "chat_threads", lambda rows: rows[0].pop("active_profile_revision")
        )
    expected_revision = 3 if old_v3 else 1
    with _target_store() as factory:
        db = SqlAlchemyRestoreDB(factory)
        service = AccountRestoreService(db)
        assert service.restore_from_zip(archive, user_id=ACCOUNT_A)["ok"] is True
        assert (
            service.restore_from_zip(archive, user_id=ACCOUNT_A)["counts"]["imported"]
            == 0
        )
        resolved = resolve_thread_system_profile(42, chatlog_db=db)
        assert resolved.active_profile_revision == expected_revision
        assert resolved.system_prompt == f"Prompt {expected_revision}"
        assert resolved.provider_override == "openai"
        assert resolved.model_override == f"gpt-profile-{expected_revision}"
        assert resolved.temperature_override == expected_revision / 10
        assert resolved.tool_permissions is None
        assert resolved.retrieval_config is None


@pytest.mark.parametrize("case", ["null", "unknown", "builtin", "flow"])
def test_restore_does_not_invent_ambiguous_thread_revision(tmp_path, case):
    source = ScopedExportDB()
    row = _pinned_thread()
    if case == "null":
        row["active_profile_revision"] = None
    else:
        row.pop("active_profile_revision")
        if case == "unknown":
            row["active_profile_id"] = "absent"
        elif case == "builtin":
            row["active_profile_id"] = "local_mode"
        else:
            row["metadata"] = {
                "profile_overrides": {
                    "a-1": {"profile_id": "a-1", "system_prompt": "flow"}
                }
            }
    source.threads = [row]
    with _target_store() as factory:
        db = SqlAlchemyRestoreDB(factory)
        assert (
            AccountRestoreService(db).restore_from_zip(
                _archive_bytes(source, tmp_path), user_id=ACCOUNT_A
            )["ok"]
            is True
        )
        assert db.get_chat_thread(42)["active_profile_revision"] is None


@pytest.mark.parametrize("revision", [0, -1, True, "1", 1.0, 99])
def test_invalid_thread_pin_fails_before_any_restore_writes(tmp_path, revision):
    source = ScopedExportDB()
    source.threads = [_pinned_thread()]
    archive = _rewrite_payload(
        _archive_bytes(source, tmp_path),
        "chat_threads",
        lambda rows: rows[0].update(active_profile_revision=revision),
    )
    with _target_store() as factory:
        db = SqlAlchemyRestoreDB(factory)
        with pytest.raises(AccountRestoreValidationError):
            AccountRestoreService(db).restore_from_zip(archive, user_id=ACCOUNT_A)
        assert db.threads == {}
        assert persona_store.list_persona_profiles(account_id=ACCOUNT_A) == []


@pytest.mark.integration
@pytest.mark.parametrize("old_v3", [False, True])
def test_production_postgres_thread_pin_export_restore(
    temporary_postgres, tmp_path, monkeypatch, old_v3
):
    from sqlalchemy import text

    from guardian.cognition.system_profiles.resolver import (
        resolve_thread_system_profile,
        switch_thread_profile,
    )
    from tests.migration.test_persona_profile_manifest_binding_migration import _upgrade

    config, database_url = temporary_postgres
    _upgrade(config, "d4e0f2a5b7c9")
    engine = create_engine(database_url)
    factory = sessionmaker(bind=engine, future=True)
    persona_store._set_session_factory(factory)
    plain_dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
    monkeypatch.setattr(pgdb_module, "_resolve_dsn", lambda: plain_dsn)
    db = pgdb_module.PgDB(plain_dsn)
    try:
        with factory.begin() as session:
            session.add(
                User(
                    id=ACCOUNT_A, username=ACCOUNT_A, password_hash="test", role="guest"
                )
            )
        persona_store.create_persona_profile(
            account_id=ACCOUNT_A,
            profile_id="recovery-pin",
            name="Historical Persona",
            system_prompt="Historical prompt.",
            model_provider="openai",
            model_id="historical-model",
            temperature=0.25,
        )
        with engine.begin() as conn:
            thread_id = conn.execute(
                text(
                    "INSERT INTO chat_threads (user_id, title) VALUES (:owner, 'recovery') RETURNING id"
                ),
                {"owner": ACCOUNT_A},
            ).scalar_one()
        before = switch_thread_profile(thread_id, "recovery-pin", chatlog_db=db)
        persona_store.update_persona_profile(
            "recovery-pin",
            account_id=ACCOUNT_A,
            name="Current Persona",
            system_prompt="Current prompt.",
            model_provider="anthropic",
            model_id="current-model",
            temperature=0.75,
        )
        archive = _archive_bytes(pgdb_module, tmp_path)
        _, payloads = _read_archive(archive)
        assert payloads["chat_threads"][0]["active_profile_revision"] == 1
        if old_v3:
            archive = _rewrite_payload(
                archive,
                "chat_threads",
                lambda rows: rows[0].pop("active_profile_revision"),
            )
        # Empty only the source fixture in this disposable Alembic database.
        # The authenticated target account remains for full-account restore.
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM chat_threads WHERE id = :id"), {"id": thread_id}
            )
            conn.execute(text("DELETE FROM persona_profiles WHERE id = 'recovery-pin'"))
        service = AccountRestoreService(db)
        assert service.restore_from_zip(archive, user_id=ACCOUNT_A)["ok"] is True
        assert (
            service.restore_from_zip(archive, user_id=ACCOUNT_A)["counts"]["imported"]
            == 0
        )
        restored = resolve_thread_system_profile(thread_id, chatlog_db=db)
        if old_v3:
            assert restored.active_profile_revision == 2
            assert (
                restored.name,
                restored.system_prompt,
                restored.provider_override,
                restored.model_override,
                restored.temperature_override,
            ) == (
                "Current Persona",
                "Current prompt.",
                "anthropic",
                "current-model",
                0.75,
            )
        else:
            assert restored.model_dump() == before.model_dump()
    finally:
        persona_store._set_session_factory(None)
        db._sa_engine.dispose()
        engine.dispose()


@pytest.mark.parametrize("profile_id", [None, "absent", "b-1", {}, []])
def test_invalid_profile_revision_pair_fails_before_restore(tmp_path, profile_id):
    source = ScopedExportDB()
    source.threads = [_pinned_thread()]
    archive = _rewrite_payload(
        _archive_bytes(source, tmp_path),
        "chat_threads",
        lambda rows: rows[0].update(active_profile_id=profile_id),
    )
    with _target_store() as factory:
        db = SqlAlchemyRestoreDB(factory)
        with pytest.raises(AccountRestoreValidationError):
            AccountRestoreService(db).restore_from_zip(archive, user_id=ACCOUNT_A)
        assert db.threads == {}
        assert persona_store.list_persona_profiles(account_id=ACCOUNT_A) == []
