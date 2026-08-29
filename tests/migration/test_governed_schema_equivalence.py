"""Focused contract tests for governed PostgreSQL schema equivalence.

These tests exercise the deterministic and fail-closed library boundary with a
read-only catalog double.  Disposable PostgreSQL execution evidence is kept in
the dated proof receipt so unit tests cannot accidentally touch a live or
shared database.
"""

from __future__ import annotations

import copy
import inspect
import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import governed_schema_equivalence as gse


def _descriptors() -> dict[str, Any]:
    return {
        "relations": [
            {"schema": "public", "name": relation}
            for relation in gse.GOVERNED_RELATIONS
        ],
        "columns": [
            {
                "schema": "public",
                "relation": relation,
                "ordinal": 1,
                "name": "id",
                "type": "character varying(36)",
                "not_null": True,
                "default": "",
                "identity": "",
                "generated": "",
                "collation": "",
            }
            for relation in gse.GOVERNED_RELATIONS
        ],
        "constraints": [
            {
                "schema": "public",
                "relation": "github_watchdog_review_attempts",
                "name": "ck_github_watchdog_review_attempts_state",
                "type": "c",
                "deferrable": False,
                "initially_deferred": False,
                "on_delete": "NOT APPLICABLE",
                "on_update": "NOT APPLICABLE",
                "definition": "CHECK ((attempt_state)::text = ANY (...))",
                "local_columns": [],
                "referenced_relation": "",
                "referenced_columns": [],
            },
            {
                "schema": "public",
                "relation": "github_watchdog_review_attempts",
                "name": "fk_github_watchdog_review_attempts_trigger_receipt_id",
                "type": "f",
                "deferrable": False,
                "initially_deferred": False,
                "on_delete": "RESTRICT",
                "on_update": "NO ACTION",
                "definition": "FOREIGN KEY (trigger_receipt_id) REFERENCES github_watchdog_delivery_receipts(receipt_id) ON DELETE RESTRICT",
                "local_columns": ["trigger_receipt_id"],
                "referenced_relation": "public.github_watchdog_delivery_receipts",
                "referenced_columns": ["receipt_id"],
            },
        ],
        "indexes": [
            {
                "schema": "public",
                "relation": relation,
                "name": f"ix_{relation}_id",
                "unique": False,
                "primary": False,
                "definition": f"CREATE INDEX ix_{relation}_id ON public.{relation} USING btree (id)",
                "predicate": "",
            }
            for relation in gse.GOVERNED_RELATIONS
        ],
    }


class _Cursor:
    def __init__(self, connection: "_CatalogConnection") -> None:
        self.connection = connection
        self.result: list[Any] = []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, statement: str, parameters: tuple[Any, ...] = ()) -> None:
        self.connection.executed.append(statement)
        self.result = self.connection.result_for(statement, parameters)

    def fetchall(self) -> list[Any]:
        return self.result


class _CatalogConnection:
    def __init__(
        self,
        *,
        database_name: str = "codexify_gse_source",
        major: int = 15,
        revisions: tuple[str, ...] = (gse.EXPECTED_ALEMBIC_REVISION,),
        descriptors: dict[str, Any] | None = None,
    ) -> None:
        self.database_name = database_name
        self.major = major
        self.revisions = revisions
        self.descriptors = descriptors or _descriptors()
        self.executed: list[str] = []

    def __enter__(self) -> "_CatalogConnection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        return _Cursor(self)

    def result_for(self, statement: str, _parameters: tuple[Any, ...]) -> list[Any]:
        if "current_setting('server_version_num')" in statement:
            return [[f"{self.major}0018"]]
        if "current_database()" in statement:
            return [[self.database_name]]
        if "to_regclass('public.alembic_version')" in statement:
            return [[True]]
        if "FROM public.alembic_version" in statement:
            return [[revision] for revision in self.revisions]
        if "c.relkind IN" in statement:
            return [[relation] for relation in gse.GOVERNED_RELATIONS]
        if "FROM pg_attribute" in statement:
            return [
                [
                    row["schema"],
                    row["relation"],
                    row["ordinal"],
                    row["name"],
                    row["type"],
                    row["not_null"],
                    row["default"],
                    row["identity"],
                    row["generated"],
                    row["collation"],
                ]
                for row in self.descriptors["columns"]
            ]
        if "FROM pg_constraint" in statement:
            return [
                [
                    row["schema"],
                    row["relation"],
                    row["name"],
                    row["type"],
                    row["deferrable"],
                    row["initially_deferred"],
                    {"RESTRICT": "r", "NO ACTION": "a"}.get(row["on_delete"], ""),
                    {"RESTRICT": "r", "NO ACTION": "a"}.get(row["on_update"], ""),
                    row["definition"],
                    row["local_columns"],
                    row["referenced_relation"],
                    row["referenced_columns"],
                ]
                for row in self.descriptors["constraints"]
            ]
        if "FROM pg_index" in statement:
            return [
                [
                    row["schema"],
                    row["relation"],
                    row["name"],
                    row["unique"],
                    row["primary"],
                    row["definition"],
                    row["predicate"],
                ]
                for row in self.descriptors["indexes"]
            ]
        raise AssertionError(f"unexpected catalog query: {statement}")


def _snapshot(
    descriptors: dict[str, Any] | None = None,
    *,
    major: int = 15,
    revision: str = gse.EXPECTED_ALEMBIC_REVISION,
) -> gse.GovernedSchemaSnapshot:
    return gse.build_snapshot(
        descriptors or _descriptors(),
        postgres_major_value=major,
        source_revision=revision,
    )


def test_v1_identifier_and_full_governed_relation_surface_are_fixed() -> None:
    assert gse.CONTRACT_VERSION == "governed-schema-equivalence/v1"
    assert len(gse.GOVERNED_RELATIONS) == 6
    assert gse.GOVERNED_RELATIONS[-1] == "notion_connection_credentials"
    snapshot = _snapshot()
    envelope = gse.serialize_envelope(snapshot.envelope())
    assert b'"contract_version":"governed-schema-equivalence/v1"' in envelope
    assert b'"postgres_major":15' in envelope
    assert b'"source_revision":"9c66e490a42b"' in envelope


@pytest.mark.parametrize(
    ("major", "revision", "error_type"),
    [
        (16, gse.EXPECTED_ALEMBIC_REVISION, gse.PostgresMajorMismatch),
        (gse.EXPECTED_POSTGRES_MAJOR, "6e9f0a1b2c3", gse.AlembicRevisionMismatch),
    ],
)
def test_v1_snapshot_identity_cannot_be_overridden(
    major: int,
    revision: str,
    error_type: type[gse.ContractError],
) -> None:
    with pytest.raises(error_type):
        _snapshot(major=major, revision=revision)


@pytest.mark.parametrize(
    "arguments",
    [
        ["inspect", "--dsn=source", "--postgres-major=16"],
        ["inspect", "--dsn=source", "--revision=6e9f0a1b2c3"],
        [
            "canonicalize",
            "--source-dsn=source",
            "--target-dsn=target",
            "--target-disposable-name=codexify_gse_target",
            "--output=snapshot.json",
            "--postgres-major=16",
        ],
        [
            "canonicalize",
            "--source-dsn=source",
            "--target-dsn=target",
            "--target-disposable-name=codexify_gse_target",
            "--output=snapshot.json",
            "--revision=6e9f0a1b2c3",
        ],
    ],
)
def test_v1_cli_rejects_contract_identity_overrides(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        gse._parser().parse_args(arguments)
    assert error.value.code == 2


def test_deterministic_serialization_orders_rows_and_json_keys() -> None:
    first = _descriptors()
    shuffled = copy.deepcopy(first)
    shuffled["columns"].reverse()
    shuffled["constraints"].reverse()
    shuffled["indexes"].reverse()

    left = _snapshot(first)
    right = _snapshot(shuffled)

    assert left.digest == right.digest
    assert gse.serialize_envelope(left.envelope()) == gse.serialize_envelope(
        right.envelope()
    )
    assert gse.serialize_envelope(left.envelope()).endswith(b"\n")


def test_descriptor_schema_preserves_fk_target_columns_and_actions() -> None:
    collected = gse.collect_governed_descriptors(_CatalogConnection())
    foreign_key = next(row for row in collected["constraints"] if row["type"] == "f")
    assert foreign_key["local_columns"] == ["trigger_receipt_id"]
    assert foreign_key["referenced_relation"] == (
        "public.github_watchdog_delivery_receipts"
    )
    assert foreign_key["referenced_columns"] == ["receipt_id"]
    assert foreign_key["on_delete"] == "RESTRICT"
    assert foreign_key["on_update"] == "NO ACTION"


def test_v1_does_not_rewrite_internal_check_parse_text() -> None:
    source = inspect.getsource(gse.collect_governed_descriptors)
    assert "conbin" not in source
    descriptors = gse.collect_governed_descriptors(_CatalogConnection())
    check = next(row for row in descriptors["constraints"] if row["type"] == "c")
    assert check["definition"] == "CHECK ((attempt_state)::text = ANY (...))"


def test_comparison_requires_exact_descriptors_even_if_digest_is_same() -> None:
    left = _snapshot()
    changed = copy.deepcopy(left.descriptors)
    changed["columns"][0]["not_null"] = not changed["columns"][0]["not_null"]
    right = replace(left, descriptors=changed, digest=left.digest)

    result = gse.compare_snapshots(left, right)

    assert result.equivalent is False
    assert "governed descriptors differ" in result.reasons
    assert result.descriptor_diff


def test_real_check_mutation_changes_digest_and_bounded_diff() -> None:
    baseline = _descriptors()
    mutation = copy.deepcopy(baseline)
    mutation["constraints"][0]["definition"] = (
        "CHECK ((attempt_state)::text <> 'running')"
    )

    left = _snapshot(baseline)
    right = _snapshot(mutation)
    result = gse.compare_snapshots(left, right)

    assert left.digest != right.digest
    assert result.equivalent is False
    assert any("constraints[" in line for line in result.descriptor_diff)
    assert len(result.descriptor_diff) <= 24
    assert sum(map(len, result.descriptor_diff)) <= 6000 + 40


def test_non_check_mutation_changes_digest_and_diff() -> None:
    mutation = copy.deepcopy(_descriptors())
    mutation["indexes"].append(
        {
            "schema": "public",
            "relation": "github_watchdog_review_attempts",
            "name": "gse_semantic_index_mutation",
            "unique": False,
            "primary": False,
            "definition": "CREATE INDEX gse_semantic_index_mutation ON public.github_watchdog_review_attempts USING btree (head_sha)",
            "predicate": "",
        }
    )

    left = _snapshot()
    right = _snapshot(mutation)
    result = gse.compare_snapshots(left, right)

    assert left.digest != right.digest
    assert result.equivalent is False
    assert any("indexes[" in line for line in result.descriptor_diff)


def test_postgres_major_mismatch_fails_closed() -> None:
    connection = _CatalogConnection(major=16)
    with pytest.raises(gse.PostgresMajorMismatch) as error:
        gse.verify_source_metadata(connection)
    assert error.value.code == "POSTGRES_MAJOR_MISMATCH"
    assert error.value.expected == 15
    assert error.value.observed == 16


def test_alembic_revision_mismatch_fails_closed() -> None:
    connection = _CatalogConnection(revisions=("6e9f0a1b2c3",))
    with pytest.raises(gse.AlembicRevisionMismatch) as error:
        gse.verify_source_metadata(connection)
    assert error.value.code == "ALEMBIC_REVISION_MISMATCH"
    assert error.value.observed == ("6e9f0a1b2c3",)


def test_missing_governed_relation_fails_closed() -> None:
    connection = _CatalogConnection()
    original = connection.result_for

    def missing_relation(statement: str, parameters: tuple[Any, ...]) -> list[Any]:
        if "c.relkind IN" in statement:
            return [[relation] for relation in gse.GOVERNED_RELATIONS[:-1]]
        return original(statement, parameters)

    connection.result_for = missing_relation  # type: ignore[method-assign]
    with pytest.raises(gse.MissingGovernedRelation) as error:
        gse.collect_governed_descriptors(connection)
    assert error.value.missing == ("notion_connection_credentials",)


def test_canonicalization_uses_one_dump_and_one_clean_restore_without_source_writes() -> (
    None
):
    source = _CatalogConnection(database_name="codexify_gse_source")
    target = _CatalogConnection(database_name="codexify_gse_target")
    connections = {
        "source-dsn": source,
        "target-dsn": target,
    }
    commands: list[tuple[list[str], dict[str, Any]]] = []

    def connect(dsn: str) -> _CatalogConnection:
        return connections[dsn]

    def run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        commands.append((command, kwargs))
        if command[0] == "pg_dump":
            return SimpleNamespace(returncode=0, stdout=b"-- schema-only dump")
        return SimpleNamespace(returncode=0, stdout=b"")

    snapshot = gse.canonicalize_database(
        "source-dsn",
        "target-dsn",
        target_disposable_name="codexify_gse_target",
        connect_factory=connect,
        run_command=run,
    )

    assert snapshot.source_revision == gse.EXPECTED_ALEMBIC_REVISION
    assert [command[0] for command, _kwargs in commands] == ["pg_dump", "psql"]
    assert commands[0][0][1:4] == [
        "--schema-only",
        "--no-owner",
        "--no-privileges",
    ]
    assert "--clean" not in commands[0][0]
    assert "--create" not in commands[0][0]
    assert all(
        statement.lstrip().upper().startswith("SELECT") for statement in source.executed
    )


def test_schema_only_source_requires_explicit_carried_revision() -> None:
    source = _CatalogConnection(
        database_name="codexify_gse_schema_only",
        revisions=(),
    )
    target = _CatalogConnection(database_name="codexify_gse_schema_target")
    connections = {
        "schema-source": source,
        "schema-target": target,
    }

    def connect(dsn: str) -> _CatalogConnection:
        return connections[dsn]

    def run(_command: list[str], **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=b"-- schema-only dump")

    with pytest.raises(gse.AlembicRevisionMismatch):
        gse.canonicalize_database(
            "schema-source",
            "schema-target",
            target_disposable_name="codexify_gse_schema_target",
            connect_factory=connect,
            run_command=run,
        )

    snapshot = gse.canonicalize_database(
        "schema-source",
        "schema-target",
        target_disposable_name="codexify_gse_schema_target",
        carried_source_revision=gse.EXPECTED_ALEMBIC_REVISION,
        connect_factory=connect,
        run_command=run,
    )
    assert snapshot.source_revision == gse.EXPECTED_ALEMBIC_REVISION


def test_canonicalization_requires_explicit_disposable_target() -> None:
    with pytest.raises(gse.DisposableTargetRequired):
        gse.canonicalize_database(
            "source-dsn",
            "target-dsn",
            target_disposable_name="production",
            connect_factory=lambda _dsn: _CatalogConnection(),
        )


def test_snapshot_round_trip_validates_digest_and_rejects_tampering(tmp_path) -> None:
    snapshot = _snapshot()
    document = snapshot.as_dict()
    assert gse.snapshot_from_dict(document).digest == snapshot.digest

    document["descriptors"]["columns"][0]["name"] = "tampered"
    with pytest.raises(gse.InvalidSnapshot):
        gse.snapshot_from_dict(document)

    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot.as_dict()), encoding="utf-8")
    assert (
        gse.snapshot_from_dict(json.loads(path.read_text())).digest == snapshot.digest
    )


def test_descriptor_diff_is_bounded_for_large_mutation() -> None:
    left = _descriptors()
    right = copy.deepcopy(left)
    right["columns"] = [
        {**row, "name": f"changed_{index}"}
        for index, row in enumerate(right["columns"])
    ]
    differences = gse.descriptor_diff(left, right, max_items=2, max_chars=120)
    assert len(differences) <= 3
    assert any("truncated" in line for line in differences)
